# Non-Photorealistic Rendering Done The Chase Way™

A collection of shaders and tools for creating and rendering cartoon meshes.

The shading model is a collection of techniques (see References) combined with my own experimental techniques for easier artist-driven detail work. 

Rough idea: This shader performs flat three tone (spec, diffuse, shadow) lighting based on vertex colors, and adds silhouette and hand-painted crease edges to the geometry. (Crease is legacy terminology that I need to change). It makes several attempts to maintain a more 2D artstyle, e.g. by having edge widths uniform in screen space and changing how the light models behaves to make things a little less realistic, and hopefully overcome some of the weaknesses of traditional NPR methods.

tl;dr - make 3D thing more 2D thing, hopefully. 

## Requirements

* Maya 2018+ with the GLSL Shader plugin enabled

## Maya Configuration Notes

* Disable "[Consolidate World](https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2016/ENU/Maya/files/GUID-9BBB6035-2A02-41BB-AF2D-99D9BEE580F1-htm.html)" in the viewport. Geometry shader(s) currently cannot handle Maya's attempt at optimizing geometry caches.

## Material Configurations

(... I'll clean this up once it's more fixed)

### Color

Color information comes from vertex painting the RGB channels of the `crease` colorset. Creases and silhouettes inherit the 

### LOD

Each crease can be assigned an LOD (0-2). Each LOD is currently associated with a maximum distance from the origin of the mesh to the camera.

### Crease Sets

Each painted crease can be given a specific set number that corresponds with additional uniform metadata about how creases in that set should be rendered - allowing for different rendering methods of groups of creases on the same mesh. 



## TODO

* Light cookies / decal for texture-driven specular reflections. 
* Experiment with triplanar texturing for edges
* Experiment with migrating GS code into a PN-AEN tessellation pipeline instead to reduce the amount of overhead calculations (performing edge detection prior to tessellation, rather than after on a larger number of edges). UE4 supports [providing adjacency information](https://github.com/EpicGames/UnrealEngine/blob/08ee319f80ef47dbf0988e14b546b65214838ec4/Engine/Source/Runtime/Engine/Private/TessellationRendering.cpp#L61) to the [tessellation pipeline](https://github.com/EpicGames/UnrealEngine/blob/08ee319f80ef47dbf0988e14b546b65214838ec4/Engine/Shaders/Private/PNTriangles.ush#L7) so it should be safe to utilize Maya's GLSL_PNAEN9 to its fullest. 
* UE4-style LODs using screen space sizes of mesh bounding boxes instead of position distances
* Resolve remaining z-order issues from edges to eliminate any uniform adjustments to make it "just right" per mesh. 
* Transparency
* Sharp texture mapping and decals 
* Better draw modes for Maya to avoid hiding vertex/edge selections behind geometry
* Silhouette control painting (variable widths, rejection)
* Better shadows (low priority though - this will end up being *very* engine-specific)


## References

Bærentzen, J. A., Munk-Lund, S., Gjøl, M., & Larsen, B. D. (2008). Two Methods for Antialiased Wireframe
Drawing with Hidden Line Removal. _Proceedings of the Spring Conference in Computer Graphics_

DesLauriers, M. (2015). Drawing Lines is Hard. Retrieved from [https://mattdesl.svbtle.com/drawing-lines-is-hard](https://mattdesl.svbtle.com/drawing-lines-is-hard)

Hajagos, B., Szécsi, L., & Csébfalvi, B. (2013). Fast silhouette and crease edge synthesis with geometry shaders. _Budapest University of Technology and Economics_

Rideout, P. (2010). Antialiased Cel Shading. Retrieved from [https://prideout.net/blog/old/blog/index.html@p=22.html](https://prideout.net/blog/old/blog/index.html@p=22.html)
