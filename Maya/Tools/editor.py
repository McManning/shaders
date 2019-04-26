"""
    Maya Editor Dialog to go alongside the NPR shader suite.

    Install as a shelf button.

    @author Chase McManning <mcmanning.1@osu.edu>
"""
import maya.cmds as cmds
import math

TITLE = "NPR Shader Tools"
VERSION = "0.2"

# Up/forward may swap depending on what workspace we're in (UE4 vs Maya)
RIGHT = 0 # X
UP = 1 # Y
FORWARD = 2 # Z

# Shader vec3 uniform to store BBox calculations
BOUNDING_BOX_UNIFORM = 'u_BoundingBox'

ABOUT_MESSAGE = """
{}

Version: {}
Author: Chase McManning <mcmanning.1@osu.edu>
""".format(TITLE, VERSION)

CREASE_COLORSET = "colorSet"

def damm(val):
    # Damm Algorithm matrix is sourced from:
    # https://en.wikibooks.org/wiki/Algorithm_Implementation/Checksums/Damm_Algorithm#Python
    matrix = (
        (0, 3, 1, 7, 5, 9, 8, 6, 4, 2),
        (7, 0, 9, 2, 1, 5, 4, 8, 6, 3),
        (4, 2, 0, 6, 8, 7, 1, 3, 5, 9),
        (1, 7, 5, 0, 9, 8, 3, 4, 2, 6),
        (6, 1, 2, 3, 0, 4, 5, 9, 7, 8),
        (3, 6, 7, 4, 2, 0, 9, 5, 8, 1),
        (5, 8, 6, 9, 7, 2, 0, 1, 3, 4),
        (8, 9, 4, 5, 3, 6, 2, 0, 1, 7),
        (9, 4, 3, 8, 6, 1, 7, 2, 0, 5),
        (2, 5, 8, 1, 4, 3, 6, 7, 9, 0)
    )

    # interim = 0
    # interim = matrix[interim][math.floor(val/ 100)]
    # interim = matrix[interim][math.floor(val % 100 / 10)]
    # interim = matrix[interim][val % 10]

    # Needs to support 3 or 4 digit numbers (for both encoding & decoding), 
    # so we instead stringify and loop
    sval = str(int(val))
    interim = 0

    for c in sval:
        interim = matrix[interim][int(c)]

    return interim

def getAverageBoundingBox(shapes):
    pass

def getMaxBoundingBox(shapes):
    """Return max bbox extents for all the input shapes

        :shapes string[] DAG object list

        :return Tuple (x, y, z)
    """
    # Calculate maximum BBox extents from all the connected shapes
    shape = shapes.pop()
    bboxMin = cmds.getAttr(shape + '.boundingBoxMin')[0]
    bboxMax = cmds.getAttr(shape + '.boundingBoxMax')[0]

    width = bboxMax[RIGHT] - bboxMin[RIGHT]
    height = bboxMax[UP] - bboxMin[UP]
    depth = bboxMax[FORWARD] - bboxMin[FORWARD]

    for shape in shapes:
        bboxMin = cmds.getAttr(shape + '.boundingBoxMin')[0]
        bboxMax = cmds.getAttr(shape + '.boundingBoxMax')[0]

        # Maximum extents
        width = max(width, bboxMax[RIGHT] - bboxMin[RIGHT])
        height = max(height, bboxMax[UP] - bboxMin[UP])
        depth = max(depth, bboxMax[FORWARD] - bboxMin[FORWARD])

    return (width, height, depth)

def updateShaderAggregateBoundingBox(aggregate_callable):
    """Update the u_BoundingBox uniform for all shaders attached
        to the selected object to the aggregate bounding box of 
        all shapes attached to each of those shaders. 

        This gets a bit convoluted when dealing with multiple 
        materials attached to each object and a shared BBox, but
        in production BBox will be a uniform provided per-instance
        rather than this aggregation. So this is more of an estimate
        and works best in one-material-per-object development environments.

        :aggregate_callable method to find a bounding box for a set of shapes.
            Different algorithms can swapped here (max vs average)
    """

    paths = cmds.listRelatives(fullPath=True, shapes=True, noIntermediate=True)

    # Update all attached shaders with the new extents
    for path in paths:
        engines = cmds.listConnections(path, type='shadingEngine')
        
        # Remove dupes
        engines = list(set(engines))

        for engine in engines:
            # Grab materials on that engine
            # Could also do listConnections(type='GLSLShader') but I may
            # port it in the future... so we wrap with ls() instead.
            materials = cmds.ls(cmds.listConnections(engine), mat=True)
            materials = list(set(materials))
        
            # Grab all shapes connected to that engine
            shapes = cmds.listConnections(engine, type='shape')

            bbox = aggregate_callable(shapes)

            # Update materials with new bounding boxe
            for material in materials:
                cmds.setAttr(material + '.' + BOUNDING_BOX_UNIFORM + 'X', bbox[0])
                cmds.setAttr(material + '.' + BOUNDING_BOX_UNIFORM + 'Y', bbox[1])
                cmds.setAttr(material + '.' + BOUNDING_BOX_UNIFORM + 'Z', bbox[2])

def about(window):
    """Prompt with an about dialog"""
    cmds.confirmDialog(
        title="About",
        message=ABOUT_MESSAGE,
        button="Close",
        defaultButton="Close",
        parent=window
    )

def getParent(selector):
    # TODO: Probably a less dumb way of doing this.
    # listRelatives(parent=True) + some checking if we're already
    # the parent, maybe?
    if selector.find('.') >= 0:
        selector = selector[:selector.find('.')]

    return selector

def setColorset():
    """Make sure the mesh has the right colorset enabled"""
    # Try to switch to the crease colorset. If we can't, make one. 
    try:
        cmds.polyColorSet(currentColorSet=True, colorSet=CREASE_COLORSET)
    except RuntimeError:
        cmds.polyColorSet(create=True, colorSet=CREASE_COLORSET)
        cmds.polyColorSet(currentColorSet=True, colorSet=CREASE_COLORSET)

    """TODO: Also apply the colorset to the shader if not already. E.g.:

    polyColorSet -currentColorSet -colorSet "crease";
    setAttr -type "string" GLSLShader1.Color0_Source "color:crease";
    AEhwShader_varyingParameterUpdate(1,1,0);
    updateRenderOverride;
    """

def clear():
    """Modify the crease dataset for the selected vertices"""
    setColorset()
    
    # Convert selection to vertices, set alpha channel for each, 
    # then convert back to the previous selection
    selected = cmds.ls(selection=True)
    cmds.select(cmds.polyListComponentConversion(tv=True))
    cmds.polyColorPerVertex(a=0)
    cmds.select(selected)


def crease(lod, mode, bump, thickness):
    """Modify the crease dataset for the selected vertices"""
    setColorset()
    
    a = makeAlpha(lod, mode, bump, thickness)

    # Convert selection to vertices, set alpha channel for each, 
    # then convert back to the previous selection
    selected = cmds.ls(selection=True)
    cmds.select(cmds.polyListComponentConversion(tv=True))
    cmds.polyColorPerVertex(a=a)
    cmds.select(selected)


def selectCreases(lodIn=None):
    """Select all crease geometry in the object with the given LOD (or all, if not specified)"""
    # TODO: Support subset selection (select matches that are a subset of what we already selected)
    selected = cmds.ls(selection=True)
    if len(selected) < 1:
        return
    
    cmds.select(getParent(selected[0]), replace=True)
    cmds.select(cmds.polyListComponentConversion(tv=True))

    lowerBound = 0
    upperBound = 2

    if lodIn is not None:
        lowerBound = lodIn
        upperBound = lodIn

    vertices = cmds.ls(selection=True, flatten=True)
    alphas = cmds.polyColorPerVertex(query=True, a=True)

    # TODO: faster?
    subset = []
    for i in range(0, len(alphas)):
        lod, mode, bump, thickness = breakAlpha(alphas[i])
        if lod >= lowerBound and lod <= upperBound:
            subset.append(vertices[i])
    
    cmds.select(subset, replace=True)


def breakAlphaV1(a):
    """(legacy) Break alpha value into LOD, Bump, and Thickness

        Currently uses 4 decimal places for the float, 
        which should be.. safe..ish..
    """
    lod = math.floor(a * 10)
    bump = math.floor(a * 100) - lod * 10
    thickness = math.floor(a * 10000) - lod * 1000 - bump * 100
    return (lod, bump, thickness)


def breakAlpha(a):
    """Break alpha value into LOD, Mode, Bump, and Thickness

        Version 2 uses a 4 decimal places, 3 to pack the above
        and the 4th as a checksum value for the packed values.
    """
    # Default value: invalid crease
    lod = -1
    mode = 0
    bump = 0
    thickness = 0

    # Only extract from alphas with a valid checksum
    checksum = damm(math.floor(a * 10000))
    if checksum == 0:
        x = int(math.floor(a * 1000))
        lod = (x & 768) / 256
        mode = (x & 192) / 64
        bump = (x & 32) / 32
        thickness = x & 31

    return (lod, mode, bump, thickness)


def makeAlpha(lod, mode, bump, thickness):
    """Make an alpha value from LOD/mode/bump/thickness"""
    # Re-encode components into a single value
    a = int(lod) * 256 | int(mode) * 64 | int(bump) * 32 | int(thickness)

    # print('makeAlpha a: {}'.format(a))

    # Offset to the [0,1) range and append a checksum
    # An extra 0.00001 is added to correct for rounding errors 
    # with pushing between Python and Maya. Unused in decoding.
    checksum = damm(a)
    # print('makeAlpha checksum: {}'.format(checksum))

    a = (a * 100.0 + checksum * 10.0 + 1) / 100000.0

    # print('makeAlpha final: {}'.format(a))
    return a


def bumpCrease():
    """Update creased vertices in a way s.t. they cannot connect
        directly to another bumped vertex.
    """
    selected = cmds.ls(selection=True)
    if len(selected) < 1:
        return
    
    # Make sure we're working on vertices
    cmds.select(cmds.polyListComponentConversion(tv=True))
    vertices = cmds.ls(selection=True, flatten=True)
    alphas = cmds.polyColorPerVertex(query=True, a=True)

    # Actually - might be easier to just give all a static
    # offset. Because 2 verts with an offset will never
    # connect (can only be connected to a 0.X0 vertex)
    # a = math.floor(alphas[0] * 10) / 10 + 0.01
    # cmds.polyColorPerVertex(a=a)
    
    # Have to loop instead of polyColorPerVertex all at once
    # because we need to maintain LOD/thickness parts.
    for i in range(0, len(alphas)):
        lod, mode, bump, thickness = breakAlpha(alphas[i])
        print('Bump from {} - {}, {}, {}, {}'.format(alphas[i], lod, mode, bump, thickness))
        a = makeAlpha(lod, mode, 1, thickness)
        print(a)
        lod, mode, bump, thickness = breakAlpha(a)
        print('New alpha {} - {}, {}, {}, {}'.format(a, lod, mode, bump, thickness))
        cmds.select(vertices[i], replace=True)
        cmds.polyColorPerVertex(a=a)

    # Restore selection
    cmds.select(selected, replace=True)

def sharpenCrease(slider):
    """Sharpen (reduce width) of selected creased vertices.
        First vertex will be given a small width, and progress
        until the last vertex in the selection
    """
    min_thickness = cmds.floatSliderGrp(slider, query=True, value=True)
    min_thickness = min_thickness * 31

    selected = cmds.ls(orderedSelection=True, flatten=True)
    if len(selected) < 1:
        return

    # Ensure selection is a vertex list
    # cmds.select(cmds.polyListComponentConversion(tv=True))
    
    alphas = cmds.polyColorPerVertex(query=True, a=True)
    lod, mode, bump, thickness = breakAlpha(alphas.pop())

    # If minimum is greater than maximum, then all vertices will
    # gain the same thickness 
    max_thickness = max(thickness, min_thickness)

    # Edge case: if there's only one vertex selected, set that
    # vertex to whatever the slider says. 
    if len(alphas) < 1:
        max_thickness = min_thickness

    # Set the last vert in the list to maximum 
    print(selected[-1])
    print(max_thickness)

    cmds.select(selected[-1], replace=True)
    cmds.polyColorPerVertex(a=makeAlpha(lod, mode, bump, max_thickness))
    
    # Set every other vert in the list to increment to the local maximum 
    flen = len(alphas) * 1.0
    for i in range(0, len(alphas)):
        lod, mode, bump, thickness = breakAlpha(alphas[i])
        thickness = min_thickness + (i / flen) * (max_thickness - min_thickness)

        print(selected[i])
        print(thickness)

        cmds.select(selected[i], replace=True)
        cmds.polyColorPerVertex(a=makeAlpha(lod, mode, bump, thickness))

    # Restore selection
    cmds.select(selected, replace=True)
    selected = cmds.ls(orderedSelection=True, flatten=True)
    print('-----')
    print(selected)
    alphas = cmds.polyColorPerVertex(query=True, a=True)
    print(alphas)


def softenModel():
    """Applies polySoftEdge softening to all edges in the model"""
    # select all edges of the parent, soften, and return to old selection
    selected = cmds.ls(selection=True)

    cmds.select(getParent(selected[0]), replace=True)
    cmds.select(cmds.polyListComponentConversion(te=True))
    cmds.polySoftEdge(a=180)

    cmds.select(selected, replace=True)

def resetMesh():
    """Softens, deletes creases, and sets vertex colors to a sane default"""
    selected = cmds.ls(selection=True)

    cmds.select(getParent(selected[0]), replace=True)
    setColorset()

    # Soften all edges
    cmds.select(cmds.polyListComponentConversion(te=True))
    cmds.polySoftEdge(a=180)

    # Reset vertex colors of every vertex to white + no crease data
    cmds.select(cmds.polyListComponentConversion(tv=True))
    cmds.polyColorPerVertex(r=1, g=1, b=1, a=0)

    # Restore selection
    cmds.select(selected, replace=True)

def migrate1to2():
    """Migrate version 1 of the alpha set of a mesh to version 2.
    
        v2 adds an extra 'mode' value (0-3), reduces storage space 
        of thickness to [0, 31], clumps values closer together with
        the amount of bits actually needed and then adds a Damm algorithm
        checksum as a last digit. 
    """
    selected = cmds.ls(selection=True)
    cmds.select(cmds.polyListComponentConversion(tv=True))

    vertices = cmds.ls(selection=True, flatten=True)
    alphas = cmds.polyColorPerVertex(query=True, a=True)

    for i in range(len(alphas)):
        lod, bump, thickness = breakAlphaV1(alphas[i])
        mode = 0 # Not supported in v1, assume default mode 0

        if (lod > 0):
            # Scale thickness down to [0,31] from [0,99]
            thickness = math.floor(thickness / 3.1)

            # Lower LOD by 1 value so LOD0 = 0, etc
            lod = lod - 1

            a = makeAlpha(lod, mode, bump, thickness)

            cmds.select(vertices[i], replace=True)
            cmds.polyColorPerVertex(a=a)
    
    # Restore selection
    cmds.select(selected, replace=True)

def testA():
    selected = cmds.ls(selection=True)
    cmds.select(cmds.polyListComponentConversion(tv=True))
    alphas = cmds.polyColorPerVertex(query=True, a=True)

    for alpha in alphas:
        lod, mode, bump, thickness = breakAlpha(alpha)
        print('{} - LOD: {}, Mode: {}, Bump: {}, Thickness: {}'.format(
            alpha, lod, mode, bump, thickness
        ))

    # Restore selection
    cmds.select(selected, replace=True)


def addMenuBar(window):
    """Add dropdown menu bar"""
    cmds.menuBarLayout()
    # cmds.menu(label="File")
    # cmds.menu(label="Display")
    # cmds.menuItem(label="")

    cmds.menu(label="Help", helpMenu=True)
    cmds.menuItem(label="About", command="about(\"" + window + "\")")
    cmds.setParent("..")

    

def addDrawModes(window):
    """Global draw overrides. Shortcut so we don't have to access shader settings per-instance"""
    cmds.rowLayout(numberOfColumns=5)
    cmds.button(label="Wireframe", command="drawMode(0)")
    cmds.button(label="Modeling", command="drawMode(1)")
    cmds.button(label="Silhouette", command="drawMode(2)")
    cmds.button(label="Unlit", command="drawMode(3)")
    cmds.button(label="Lookdev", command="drawMode(4)")
    cmds.setParent("..")

def addCreaseGroup(window):
    """Crease editing tools"""
    cmds.frameLayout(label="Edit Creases")
    cmds.text(label="Words here")

    cmds.rowLayout(numberOfColumns=4)
    cmds.button(label="Clear Selected", command="clear()")
    cmds.button(label="Crease (LOD0)", command="crease(0, 0, 0, 31)")
    cmds.button(label="Crease (LOD1)", command="crease(1, 0, 0, 31)")
    cmds.button(label="Crease (LOD2)", command="crease(2, 0, 0, 31)")
    cmds.setParent("..")

    cmds.rowLayout(numberOfColumns=4)
    cmds.button(label="Select All", command="selectCreases()")
    cmds.button(label="Select LOD0", command="selectCreases(0.10)")
    cmds.button(label="Select LOD1", command="selectCreases(0.20)")
    cmds.button(label="Select LOD2", command="selectCreases(0.30)")
    cmds.setParent("..")

    cmds.columnLayout(rowSpacing=5)
    slider = cmds.floatSliderGrp(
        label="Sharpen", 
        field=True, 
        minValue=0.0, 
        maxValue=1.0, 
        fieldMinValue=0.0, 
        fieldMaxValue=1.0, 
        value=0
    )
    cmds.button(label="Sharpen", command="sharpenCrease(\"" + slider + "\")")

    cmds.setParent("..")
    cmds.setParent("..")

def addMiscGroup(window):
    """Misc relevant tools"""
    cmds.frameLayout(label="Misc Tools")
    cmds.rowColumnLayout(numberOfColumns=5)

    cmds.button(label="Soften all edges", command="softenModel()")
    cmds.button(label="Delete History", command="cmds.DeleteHistory()")
    cmds.button(label="Bump Crease", command="bumpCrease()")
    cmds.button(label="Reset Mesh", command="resetMesh()")
    cmds.button(label="Test A", command="testA()")
    cmds.button(
        label="Update BBox (MAX)", 
        command="updateShaderAggregateBoundingBox(getMaxBoundingBox)"
    )

    cmds.setParent("..")
    cmds.setParent("..")

def addLegacyGroup(window):
    cmds.frameLayout(label="Legacy")

    cmds.rowLayout(numberOfColumns=4)
    cmds.button(label="Migrate 1->2", command="migrate1to2()")

    cmds.setParent("..")
    cmds.setParent("..")

def openEditor():        
    window = cmds.window(title=TITLE, iconName=TITLE) # , widthHeight=(200, 55))
    cmds.columnLayout(adjustableColumn=True)

    addMenuBar(window)
    addDrawModes(window)
    addCreaseGroup(window)
    # cmds.separator(height=10, style="none")
    addMiscGroup(window)
    addLegacyGroup(window)
    
    cmds.showWindow(window)

openEditor()
