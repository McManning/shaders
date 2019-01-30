
import maya.cmds as cmds
import math

CREASE_COLORSET = "crease"

def about(window):
    """Prompt with an about dialog"""
    cmds.confirmDialog(
        title="About",
        message="Something here informative",
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

def crease(alpha=1.0):
    """Modify the crease dataseat for the selected vertices"""
    # Try to switch to the crease colorset. If we can't, make one. 
    try:
        cmds.polyColorSet(currentColorSet=True, colorSet=CREASE_COLORSET)
    except RuntimeError:
        cmds.polyColorSet(create=True, colorSet=CREASE_COLORSET)
        cmds.polyColorSet(currentColorSet=True, colorSet=CREASE_COLORSET)

    # Convert selection to vertices, set alpha channel for each, 
    # then convert back to the previous selection
    selected = cmds.ls(selection=True)
    cmds.select(cmds.polyListComponentConversion(tv=True))
    cmds.polyColorPerVertex(a=alpha)
    cmds.select(selected)

    """TODO: Also apply the colorset to the shader if not already. E.g.:

    polyColorSet -currentColorSet -colorSet "crease";
    setAttr -type "string" GLSLShader1.Color0_Source "color:crease";
    AEhwShader_varyingParameterUpdate(1,1,0);
    updateRenderOverride;
    """

def selectCreases(alpha=None):
    """Select all crease geometry in the object with the given alpha, or any non-zero alpha"""

    # TODO: Support subset selection (select matches that are a subset of what we already selected)
    selected = cmds.ls(selection=True)
    if len(selected) < 1:
        return
    
    cmds.select(getParent(selected[0]), replace=True)
    cmds.select(cmds.polyListComponentConversion(tv=True))

    lowerBound = 0.10 # LOD0
    upperBound = 0.39 # LOD2 upper

    if alpha is not None:
        lowerBound = alpha
        upperBound = alpha + 0.09

    vertices = cmds.ls(selection=True, flatten=True)
    alphas = cmds.polyColorPerVertex(query=True, a=True)

    # TODO: faster?
    subset = []
    for i in range(0, len(alphas)):
        if alphas[i] >= lowerBound and alphas[i] <= upperBound:
            subset.append(vertices[i])
    
    cmds.select(subset, replace=True)

def breakAlpha(a):
    """Break alpha value into LOD, Bump, and Thickness

        Currently uses 4 decimal places for the float, 
        which should be.. safe..ish..
    """
    lod = math.floor(a * 10)
    bump = math.floor(a * 100) - lod * 10
    thickness = math.floor(a * 10000) - lod * 1000 - bump * 100
    return (lod, bump, thickness)

def makeAlpha(lod, bump, thickness):
    """Make an alpha value from LOD/bump/thickness"""
    # The extra 0.00001 is just to try to hammer out potential
    # rounding errors at the lowest defined decimal. It's unused.
    return (lod * 1000 + bump * 100 + thickness) * 0.0001 + 0.00001

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
        lod, bump, thickness = breakAlpha(alphas[i])
        cmds.select(vertices[i], replace=True)
        cmds.polyColorPerVertex(a=makeAlpha(lod, 1, thickness))

    # Restore selection
    cmds.select(selected, replace=True)

def sharpenCrease(slider):
    """Sharpen (reduce width) of selected creased vertices.
        First vertex will be given a small width, and progress
        until the last vertex in the selection
    """
    min_thickness = cmds.floatSliderGrp(slider, query=True, value=True)
    min_thickness = max(0, min(min_thickness * 100, 99))

    selected = cmds.ls(orderedSelection=True, flatten=True)
    if len(selected) < 1:
        return

    # Ensure selection is a vertex list
    # cmds.select(cmds.polyListComponentConversion(tv=True))
    
    alphas = cmds.polyColorPerVertex(query=True, a=True)
    lod, bump, thickness = breakAlpha(alphas.pop())

    # If minimum is greater than maximum, then all vertices will
    # gain the same thickness 
    max_thickness = max(thickness, min_thickness)

    # Set the last vert in the list to maximum 
    print(selected[-1])
    print(max_thickness)

    cmds.select(selected[-1], replace=True)
    cmds.polyColorPerVertex(a=makeAlpha(lod, bump, max_thickness))
    
    # Set every other vert in the list to increment to the local maximum 
    flen = len(alphas) * 1.0
    for i in range(0, len(alphas)):
        lod, bump, thickness = breakAlpha(alphas[i])
        thickness = min_thickness + (i / flen) * (max_thickness - min_thickness)

        print(selected[i])
        print(thickness)

        cmds.select(selected[i], replace=True)
        cmds.polyColorPerVertex(a=makeAlpha(lod, bump, thickness))

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

def addMenuBar(window):
    """Add dropdown menu bar"""
    cmds.menuBarLayout()
    cmds.menu(label="File")
    cmds.menu(label="Help", helpMenu=True)
    cmds.menuItem(label='About', command="about(\"" + window + "\")")
    cmds.setParent("..")

def addCreaseGroup(window):
    """Crease editing tools"""
    cmds.frameLayout(label="Edit Creases")
    cmds.text(label="Words here")

    cmds.rowLayout(numberOfColumns=4)
    cmds.button(label="Clear Selected", command="crease(0.0)")
    cmds.button(label="Crease (LOD0)", command="crease(0.10991)")
    cmds.button(label="Crease (LOD1)", command="crease(0.20991)")
    cmds.button(label="Crease (LOD2)", command="crease(0.30991)")
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
    cmds.rowLayout(numberOfColumns=4)

    cmds.button(label="Soften all edges", command="softenModel()")
    cmds.button(label="Delete History", command="cmds.DeleteHistory()")

    cmds.button(label="Bump Crease", command="bumpCrease()")
    cmds.setParent("..")
    cmds.setParent("..")


def openEditor():        
    window = cmds.window(title="Shader Tools", iconName="Shader Tools") # , widthHeight=(200, 55))
    cmds.columnLayout(adjustableColumn=True)

    addMenuBar(window)
    addCreaseGroup(window)
    cmds.separator(height=10, style="none")
    addMiscGroup(window)
    
    cmds.showWindow(window)

openEditor()
