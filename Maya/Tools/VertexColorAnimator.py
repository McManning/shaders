"""Vertex Color Animation Tooling

This toolset is an attempt to resolve some of the usability 
issues with Maya's built in vertex color animation tools:

- Poor (nearly unusable) performance when dealing with larger vertex counts
- Lack of displaying keyed animation frames on the timeline 
- Difficulty in managing keyframes in the graph editor
- Cannot export animations (sans transforms and visibility) to FBX for use in Unity

TODO:
- UV indexing on export so the FBX will be able to map up vertices when loading in Unity/etc
- Vertex color animation data compressed and exported within the FBX
    (remove vertices from frames that never animate, pull keyframe timings, 
    build out a JSON blob that contains the keyframed index changes and all
    the modified vertex color data per-frame)
    
@author Chase McManning <cmcmanning@gmail.com>
"""

import sys, traceback
import json
import maya.cmds as cmds
import maya.api.OpenMaya as om

def selected_meshes():
    """Generator to return DAG paths of all selected meshes

    Returns:
        string: Selected mesh DAG path
    """
    selection = om.MGlobal.getActiveSelectionList()

    # TODO: See if there's a way to get the mesh of a selected vertex
    sel_it = om.MItSelectionList(selection)
    while not sel_it.isDone():
        dag_path = om.MDagPath()

        if sel_it.itemType() == om.MItSelectionList.kDagSelectionItem:
            dag_path = sel_it.getDagPath()

            if dag_path.hasFn(om.MFn.kMesh):
                yield dag_path

        sel_it.next()

def dag_node(xform):
    """Utility to transform a string DAG path to a node

    Parameters:
        xform (str): DAG path to parse

    Returns:
        MDagNode: Node from the path, or None if cannot be resolved
    """
    selection = om.MSelectionList()
    try:
        selection.add(xform)
    except:
        return None

    return selection.getDagPath(0)

def safe_exceptions(func):
    """Decorator to improve exception handling in Maya"""
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=10, file=sys.stdout)   
    return wrapper

class VertexColorFrame:
    """Cache information about vertex colors for a mesh

    Supports reading/writing to a mesh and converting to  
    a format for inclusion in the FBX file export
    """
    def __init__(self):
        self.cache = [] 
        self.vtx_count = 0

    def copy_from(self, mesh):
        """Copy the colors from the input mesh into this frame

        Parameters:
            mesh (MObject): Target mesh
        """
        # MColor instances are converted to Python tuples to cache,
        # as Maya will eventually unload the allocated memory 
        self.cache = [c.getColor() for c in mesh.getVertexColors()]
        self.vtx_count = len(self.cache)

    def copy_to(self, mesh):
        """Copy the colors of this frame back onto the input mesh

        Parameters:
            mesh (MObject): Target mesh
        """
        mesh.setVertexColors(self.cache, list(range(self.vtx_count)))
        # TODO: For large meshes (> 20k vertices) this isn't incredibly
        # performant. Using diff() and a subset of changed vertices might be better.

        # FORCE the viewport to reset to redraw. Shouldn't be necessary, but 
        # it seems Maya is refusing to update renders for colormaps. 
        # cmds.ogs(reset=True)

    def diff(self, frame):
        """Diff against another frame and return indices that have changed

        Parameters:
            frame (VertexColorFrame): State to diff against

        Returns:
            list: Vertex IDs that have changed
        """
        
        # Vertices that are out of bounds on this 
        # if frame.vtx_count < self.vtx_count:
        #    oob = list(range(frame.vtx_count, self.vtx_count)

        indices = [x for x in range(self.vtx_count) if self.cache[x] == frame.cache[x]]

        # TODO: Deal with different cache sizes

        return indices

    def is_different(self, frame):
        """Check for any changed vertex color

        Parameters:
            frame (VertexColorFrame): State to diff against

        Returns:
            bool: If any vertices have changed
        """
        for i in range(self.vtx_count):
            if self.cache[i] != frame.cache[i]:
                return True
        
        return False

    def deserialize(self, cache):
        self.cache = cache
        self.vtx_count = len(self.cache)

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

    def __init__(self, dag_path):
        """
        Parameters:
            dag_path (MDagPath): Mesh DAG path
        """
        # Only store the string version of the path, as Maya
        # may deallocate memory between uses
        self.dag_path = om.MFnDagNode(dag_path.transform()).fullPathName()
        self.frames = []
        self.prev_frame = -1
        self.prev_idx = -1

        self.setup()

    def get_mesh(self):
        return om.MFnMesh(dag_node(self.dag_path))

    def get_attr(self, name, data_type, default_value, keyable):
        """Retrieve an attribute by name, creating if it does not exist

        Parameters:
            name (str):
            data_type (str)
            default_value (any):
            keyable (bool):

        Returns:
            any: The attribute value, or default_value if it did not exist
        """
        try:
            value = cmds.getAttr('{}.{}'.format(self.dag_path, name))
        except ValueError:
            print(name, data_type)

            # TODO: Cleanup this weird workaround. Maya is complaining that it 
            # doesn't recognize the type when setting.
            if data_type == 'string':
                cmds.addAttr(self.dag_path, longName=name, dataType=data_type, keyable=keyable)
                cmds.setAttr('{}.{}'.format(self.dag_path, name), default_value, type=data_type, keyable=keyable)
            else:
                cmds.addAttr(self.dag_path, longName=name, attributeType=data_type, keyable=keyable)
                cmds.setAttr('{}.{}'.format(self.dag_path, name), default_value, keyable=keyable)
            
            value = default_value

        return value

    def set_attr(self, name, data_type, value, keyable):
        current_value = self.get_attr(name, data_type, value, keyable)

        if current_value != value:
            if data_type == 'string':
                cmds.setAttr('{}.{}'.format(self.dag_path, name), value, type=data_type, keyable=keyable)
            else:
                cmds.setAttr('{}.{}'.format(self.dag_path, name), value, keyable=keyable)

    def setup(self):
        """Setup necessary attribute defaults for the bound mesh and load cache"""
        vci = self.get_attr(self.ATTR_VCI, 'short', 0, True)
        export = self.get_attr(self.ATTR_EXPORT, 'string', '', False)

        self.load_cache()

    def load_cache(self):
        """Load cache data into the animator, replacing what is already setup"""
        encoded = self.get_attr(self.ATTR_CACHE, 'string', '[]', False)
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
        self.set_attr(self.ATTR_CACHE, 'string', encoded, False)

    def on_frame_change(self, frame):
        """Event handler to change the VertexColorFrame rendered onto the mesh
        
        Parameters:
            frame (int): new frame number
        """
        if frame == self.prev_frame:
            return
        
        self.prev_frame = frame

        idx = self.get_attr(self.ATTR_VCI, 'short', 0, True)
        if idx == self.prev_idx:
            return 

        print('Transition {} to VCI {}'.format(self.dag_path, idx))
        self.prev_idx = idx
        self.frames[idx].copy_to(self.get_mesh())
    
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
        new_frame.copy_from(self.get_mesh())

        if len(self.frames) > 0:
            # If the colors of the mesh have changed, store the new VCF 
            if self.frames[vci].is_different(new_frame):
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
            '{}.{}'.format(self.dag_path, self.ATTR_VCI), 
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
            self.dag_path,
            attribute=self.ATTR_VCI, 
            inTangentType='stepnext', 
            outTangentType='step'
        )

        self.set_attr(self.ATTR_VCI, 'short', vci, True)


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
    @safe_exceptions
    def on_frame_change(cls, frame):
        """Delegate frame change event to *all* animators
        
        Parameters:
            frame (int): new frame number
        """
        for animator in cls.animators.values():
            animator.on_frame_change(frame)

    @classmethod
    @safe_exceptions
    def on_export(cls):
        """Event handler for export button

        Ensures all the selected objects have their export data  
        cleaned up prior to the user doing an FBX export
        """
        for animator in cls.selection_animators():
            animator.on_export()

    @classmethod
    @safe_exceptions
    def on_set_key(cls):
        """Key vertex colors on all selected objects.

        If a selection does not have an animator setup, 
        one will be created for it.
        """
        for animator in cls.selection_animators():
            animator.add_key()

    @classmethod
    def selection_animators(cls):
        """Generator for VertexColorAnimator for each selected mesh
        
        If a selected mesh does not have an animator setup for it,
        one will be created automatically and tracked. If that mesh
        has cached data associated with it, the new animator instance
        will use that cached data.

        Returns:
            VertexColorAnimator: for each mesh selected
        """
        for dag_path in selected_meshes():
            path = om.MFnDagNode(dag_path.transform()).fullPathName()
            if path not in cls.animators:
                animator = VertexColorAnimator(dag_path)
                cls.animators[path] = animator

            yield cls.animators[path]

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
