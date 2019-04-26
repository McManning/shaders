"""
    Calculate an aggregate bounding box and store into 
    each shader attached to the selected object(s)

    This is to provide a rough idea of BBox extents for LOD calculations
    in Maya while developing a new asset. Due to not being able to provide
    custom BBox uniforms per-model to the shader as we would in production,
    this is more of an estimation that tends to be more helpful while 
    developing/testing single assets than trying to composite scenes within Maya.

    @author Chase McManning <mcmanning.1@osu.edu>
"""
import maya.cmds as cmds
import maya.mel as mel

# Up/forward may swap depending on what workspace we're in (UE4 vs Maya)
RIGHT = 0 # X
UP = 1 # Y
FORWARD = 2 # Z

# Shader vec3 uniform to store BBox calculations
BOUNDING_BOX_UNIFORM = 'u_BoundingBox'

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


updateShaderAggregateBoundingBox(getMaxBoundingBox)
