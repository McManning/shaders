"""Vertex Color Animation Tooling

This toolset is an attempt to resolve some of the usability 
issues with Maya's built in vertex color animation tools:

- Poor (nearly unusable) performance when dealing with larger vertex counts
- Lack of displaying keyed animation frames on the timeline 
- Difficulty in managing keyframes in the graph editor
- Cannot export animations (sans transforms and visibility) to FBX for use in Unity

TODO:
- UV indexing so the FBX will be able to map up vertices when loading in Unity/etc

@author Chase McManning <cmcmanning@gmail.com>
"""

import sys, traceback
import json
import maya.cmds as cmds


class VertexColorFrame:
    """Cache information about vertex colors for a mesh

    Supports reading/writing to a mesh and converting to  
    a format for inclusion in the FBX file export
    """
    def __init__(self):
        """
        Parameters:
            cache (dict): Default cache
        """
        self.cache = [] 
        self.vtx_count = 0

    def copy_from(self, obj):
        """Copy the colors from the input mesh into this frame

        Parameters:
            obj (str): Target mesh
        """
        rgb = cmds.polyColorPerVertex(obj + '.vtx[*]', query=True, rgb=True)
        self.cache = rgb 
        self.vtx_count = int(len(rgb) / 3)

    def copy_to(self, obj):
        """Copy the colors of this frame back onto the input mesh

        Parameters:
            obj (str): Target mesh
        """
        rgb = cmds.polyColorPerVertex(obj + '.vtx[*]', query=True, rgb=True)
        indices = self.diff_vtx_list(rgb)
            
        # Group up indices by color.
        # TODO: Still incredibly slow for large vertex counts of the
        # target mesh (not necessarily large vertex counts to be updated)
        batches = dict()
        for vtx_id in indices:
            idx = vtx_id * 3
            rgb = (self.cache[idx], self.cache[idx + 1], self.cache[idx + 2])
            if rgb not in batches:
                batches[rgb] = ['{}.vtx[{}]'.format(obj, vtx_id)]
            else:
                batches[rgb].append('{}.vtx[{}]'.format(obj, vtx_id))
        
        for rgb in batches:
            cmds.polyColorPerVertex(batches[rgb], rgb=rgb, notUndoable=True)

        # FORCE the viewport to reset to redraw. Shouldn't be necessary, but 
        # it seems Maya is refusing to update renders for colormaps. 
        cmds.ogs(reset=True)

    def diff(self, frame):
        """Diff against another frame and return indices that have changed

        Parameters:
            frame (VertexColorFrame): State to diff against

        Returns:
            list: Vertex IDs that have changed
        """
        return self.diff_vtx_list(frame.cache)

    def diff_vtx_list(self, vtx_list):
        """Diff against another vertex list and return indices that have changed

        Parameters:
            vtx_list (list): Vertex color list 

        Returns:
            list: Vertex IDs that have changed
        """
        indices = []
        PRECISION = 0.0001

        # A. Check for a mismatched cache length, any frames outside the common length are changed.
        
        # B. Check for mismatched colors (with some tolerance) for common vertices
        a = self.cache
        b = vtx_list

        for vtx_id in range(self.vtx_count):
            idx = vtx_id * 3
            
            if abs(a[idx] - b[idx]) > PRECISION or abs(a[idx + 1] - b[idx + 1]) > PRECISION or abs(a[idx + 2] - b[idx + 2]) > PRECISION:
                indices.append(vtx_id)

        return indices

    def deserialize(self, cache):
        self.cache = cache
        self.vtx_count = int(len(cache) / 3)

    def serialize(self):
        """Return a serialized copy of this frame for caching
        
        Returns:
            list: Data to serialize
        """
        return self.cache


class VertexColorAnimator:
    """Animator instance associated with a mesh.

    Adds support for keyframing vertex colors on a mesh and exporting 
    those keyframes into FBX files through Maya's FBX exporter.

    This does *not* use Maya's built in vertex color keyframing due to 
    performance reasons, nor does it store color keying using curves in 
    the FBX file (again, perf reasons). 
    """

    # Cache data for restoring an instance of VCA on a mesh
    ATTR_CACHE = 'VCACache'

    # Keyable attribute for setting the vertex color index per-frame
    ATTR_VCI = 'VertexColorIndex'

    # Export data that will be copied to the FBX
    ATTR_EXPORT = 'VCAExport'

    def __init__(self, obj):
        self.obj = obj
        self.frames = []
        self.prev_frame = -1
        self.prev_idx = -1

        self.setup_object()

    def get_attr(self, longName, dataType, defaultValue, keyable):
        """Retrieve an attribute by longName, creating if it does not exist

        Parameters:
            longName (str):
            dataType (str)
            defaultValue (any):
            keyable (bool):

        Returns:
            any: The attribute value, or defaultValue if it did not exist
        """
        try:
            value = cmds.getAttr('{}.{}'.format(self.obj, longName))
        except ValueError:
            print(longName, dataType)

            # TODO: Cleanup this weird workaround. Maya is complaining that it 
            # doesn't recognize the type when setting.
            if dataType == 'string':
                cmds.addAttr(self.obj, longName=longName, dataType=dataType, keyable=keyable)
                cmds.setAttr('{}.{}'.format(self.obj, longName), defaultValue, type=dataType, keyable=keyable)
            else:
                cmds.addAttr(self.obj, longName=longName, attributeType=dataType, keyable=keyable)
                cmds.setAttr('{}.{}'.format(self.obj, longName), defaultValue, keyable=keyable)
            
            value = defaultValue

        return value

    def setup_object(self):
        """Setup necessary attribute defaults for the bound mesh and load cache"""
        vci = self.get_attr(
            longName=self.ATTR_VCI, 
            dataType='short', 
            defaultValue=0,
            keyable=True
        )

        export = self.get_attr(
            longName=self.ATTR_EXPORT, 
            dataType='string', 
            defaultValue='', 
            keyable=False
        )
        
        self.load_cache()

    def load_cache(self):
        """Load cache data into the animator, replacing what is already setup"""
        encoded = self.get_attr(
            longName=self.ATTR_CACHE, 
            dataType='string', 
            defaultValue='[]', 
            keyable=False
        )

        cache = json.loads(encoded)

        self.frames = []
        for frame in cache:
            new_frame = VertexColorFrame()
            new_frame.deserialize(frame)
            self.frames.append(new_frame)

    def update_cache(self):
        """Persist our current state into the cache attribute"""
        cache = []
        for frame in self.frames:
            cache.append(frame.serialize())
        
        encoded = json.dumps(cache)
        cmds.setAttr(
            '{}.{}'.format(self.obj, self.ATTR_CACHE), 
            encoded,
            type='string', 
            keyable=False
        )

    def on_frame_change(self, frame):
        """Event handler to change the VertexColorFrame rendered onto the mesh
        
        Parameters:
            frame (int): new frame number
        """
        if frame == self.prev_frame:
            return
        
        prev_frame = frame 

        idx = cmds.getAttr('{}.{}'.format(self.obj, self.ATTR_VCI))
        if idx == self.prev_idx:
            return 

        print('Transition {} to VCI {}'.format(self.obj, idx))
        self.prev_idx = idx
        self.frames[idx].copy_to(self.obj)
    
    def on_export(self):
        # TODO: Big serialization work happens here. 
        # UV indexing is setup (if not already), frames are
        # compressed and copied into a format for FBX,
        # the keyframes for VCI are serialized for FBX
        # (since that animated attribute doesn't export)
        pass

    def add_key(self):
        """Add a timeline key for the mesh and current color state"""
        vci = self.get_current_vci()

        new_frame = VertexColorFrame()
        new_frame.copy_from(self.obj)

        if len(self.frames) > 0:
            changed_indices = self.frames[vci].diff(new_frame)
            
            # If the colors of the mesh have changed, store the new VCF 
            if len(changed_indices) > 0:
                self.set_keyframe(len(self.frames))
                self.frames.append(new_frame)
                self.update_cache()
            else:
                # Nothing has changed, so we key it to the same VCI
                self.set_keyframe(vci)
        else:
            # Nothing is cached yet, set it as the first
            self.frames.append(new_frame)
            self.set_keyframe(0)
            self.update_cache()
            
    def get_current_vci(self):
        """Evaluate the current VCI that should be displayed
        
        Invalid keyframes just return as the last one in the cache

        Returns:
            int: Index at the current time 
        """
        current = cmds.keyframe(
            '{}.{}'.format(self.obj, self.ATTR_VCI), 
            query=True, 
            eval=True
        )
        
        print(current)

        if current is None:
            self.set_keyframe(0)
            current = 0
        else:
            current = int(current[0])

        return min(len(self.frames) - 1, current)

    def set_keyframe(self, vci):
        """Keyframe the VCI attribute with the input value
        
        Parameters:
            vci (int): Index to keyframe
        """
        cmds.setKeyframe(
            self.obj, 
            attribute=self.ATTR_VCI, 
            inTangentType='stepnext', 
            outTangentType='step'
        )

        cmds.setAttr('{}.{}'.format(self.obj, self.ATTR_VCI), vci)


class VertexColorAnimatorSystem:
    """Singleton system to maintain references to all VCAs and handle expression hooks

    """
    window = None

    # Mapping between an object and VertexColorAnimator
    # TODO: Handle renamed objects somehow
    animators = dict()

    WINDOW_TITLE = 'Colorkey Anim'

    @classmethod
    def initialize(cls):
        """Ensure there's a global expression setup for watching frame changes"""

        # Setup a global expression for monitoring frame changes
        name = 'VertexColorAnimatorSystem_on_frame_change'
        expression = 'python("VertexColorAnimatorSystem.on_frame_change(" + frame + ")")'

        try:
            cmds.delete(name)
        except ValueError:
            pass

        cmds.expression(name=name, s=expression)

    @classmethod
    def on_frame_change(cls, frame):
        """Delegate frame change event to all animators
        
        Parameters:
            frame (int): new frame number
        """
        for animator in cls.animators.values():
            animator.on_frame_change(frame)

    @classmethod
    def on_export(cls):
        """Event handler for export button

        Ensures all the selected objects have their export data  
        cleaned up prior to the user doing an FBX export
        """
        animators = cls.get_animators_for_selection()

        for animator in animators:
            animator.on_export()

    @classmethod
    def on_set_key(cls):
        """Key vertex colors on all selected objects.

        If a selection does not have an animator setup, 
        one will be created for it.
        """
        try:
            animators = cls.get_animators_for_selection()

            for animator in animators:
                animator.add_key()
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=10, file=sys.stdout)   

    @classmethod
    def get_animators_for_selection(cls):
        """Get or create animators for each selected object

        Returns:
            list: VertexColorAnimators
        """
        objects = cmds.ls(selection=True, objectsOnly=True)
        # TODO: Need to ensure these are the transform nodes,
        # as sometimes the above ls will return a shape instead.
        selected = []

        for obj in objects:
            if obj in cls.animators:
                selected.append(cls.animators[obj])
            else:
                animator = VertexColorAnimator(obj)
                cls.animators[obj] = animator
                selected.append(animator)

        return selected
    
    @classmethod
    def open_editor(cls):
        if not cls.window:
            cls.window = cmds.window(
                title=cls.WINDOW_TITLE, 
                iconName=cls.WINDOW_TITLE
            )
            # , widthHeight=(200, 55))
            cmds.columnLayout(adjustableColumn=True)

            cmds.frameLayout(label="Tools")
            cmds.rowColumnLayout(numberOfColumns=5)

            cmds.button(label="Set Key", command="VertexColorAnimatorSystem.on_set_key()")
            cmds.button(label="Export", command="VertexColorAnimatorSystem.on_export()")

            cmds.setParent("..")
            cmds.setParent("..")

        cmds.showWindow(cls.window)


VertexColorAnimatorSystem.initialize()
VertexColorAnimatorSystem.open_editor()
