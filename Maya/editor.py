
import maya.cmds as cmds

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

def selectCreases(alpha=None):
    """Select all crease geometry in the object with the given alpha, or any non-zero alpha"""
    selected = cmds.ls(selection=True)
    if len(selected) < 1:
        return
    
    cmds.select(getParent(selected[0]))
    cmds.select(cmds.polyListComponentConversion(tv=True))

    lowerBound = 0.0001
    upperBound = 1.1

    if alpha:
        lowerBound = alpha - 0.1
        upperBound = alpha + 0.1

    # TODO: FASTER!
    vertices = cmds.ls(selection=True, flatten=True)
    alphas = cmds.polyColorPerVertex(query=True, a=True)

    subset = []
    for i in range(0, len(alphas)):
        if alphas[i] > lowerBound and alphas[i] < upperBound:
            subset.append(vertices[i])
    
    cmds.select(subset)


def softenModel():
    """Applies polySoftEdge softening to all edges in the model"""
    # select all edges of the parent, soften, and return to old selection
    selected = cmds.ls(selection=True)

    cmds.select(getParent(selected[0]))
    cmds.select(cmds.polyListComponentConversion(te=True))
    cmds.polySoftEdge(a=180)

    cmds.select(selected)

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
    cmds.button(label="Crease (LOD0)", command="crease(0.25)")
    cmds.button(label="Crease (LOD1)", command="crease(0.75)")
    cmds.button(label="Crease (LOD2)", command="crease(1.0)")

    cmds.setParent("..")

    cmds.rowLayout(numberOfColumns=4)

    cmds.button(label="Select All", command="selectCreases()")
    cmds.button(label="Select LOD0", command="selectCreases(0.25)")
    cmds.button(label="Select LOD1", command="selectCreases(0.75)")
    cmds.button(label="Select LOD2", command="selectCreases(1.0)")

    cmds.setParent("..")

    cmds.setParent("..")

def addMiscGroup(window):
    """Misc relevant tools"""
    cmds.frameLayout(label="Misc Tools")
    cmds.rowLayout(numberOfColumns=4)

    cmds.button(label="Soften all edges", command="softenModel()")
    
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
