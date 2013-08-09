ADH Rigging Tools
=================

A collection of Blender operators for my personal rigging needs:

- **Add Subdivision Surface Modifier**. Adds subdivision surface modifier for all selected objects (except if one is already added), and gives control to their visibility. Should've been named "Add/Toggle..." but that's too unwieldy.

- **Apply Lattices**. Applies all lattice modifiers, and deletes all shapekeys. I use it for lattice-initialized shapekey creation, which for me is much faster and cleaner than plain editing and sculpting.

- **Mask Selected Vertices**. Add a Mask modifier to active mesh object, then assign selected vertices to the vertex group used as mask in the modifier. Modifier alters behavior: Shift-LMB removes selected vertices from mask vertex group, and Ctrl-LMB inverts the vertex group. Works either in Edit mode or otherwise.

- **Bind to Bone**. Binds all selected objects to selected bone, adding armature and vertex group if none exist yet. Compared to just parenting objects to the bone, this is faster while still lets us add component of the object that's controlled by another bone.

- **Copy Custom Shapes**. Copies custom shape from one armature to another (on bones with similar name). Sometimes, without knowing the cause, all custom shapes in an armature already well-fit to a character just vanishes. Gone. And it's bloody annoying to reattach them one by one, thus this operator.

- **Create Custom Shape**. Creates new custom shape object and automatically assigns it to all selected bones. Active bone's name will become the new object's base name. We can:
  - Choose among several simple predefined shapes,
  - Set the object name's prefix,
  - Set the object's size, rotation, position (along the length of bone), and scene layer.

- **Select Custom Shape**. Select active bone's custom shape object, if any. If the shape's scene layers are turned off, one is turned on. If the shape is hidden, it's made visible.

- **Create Bone Group**. Creates a new bone group, named after active bone and consisting of all selected bones. Color theme randomly selected among preset themes. If a bone group with the same name already exist, it only changes the existing bone group's color theme.

- **Create Hook Bones**. Creates parentless bone for each selected bone, local copy-transformed. My primary tool to create a lattice-based deformation with intuitive control.

- **Remove Vertex Groups of Unselected Bones**. In all selected mesh objects, this operator removes all vertex groups other than selected bones. Armature object must be active, in pose mode. I use it right after automatic weight assignment, to remove unwanted bone influence. This makes skinning much faster without sacrificing quality.

- **Rename Regex**. Renames selected objects or bones using regular expressions. Depends on re, standard library module. It's still rough on the edges, but perfectly usable.

- **Sync Object Data Name To Object**. Sync an object data's name to the object's. Made it easier to reuse object data among separate files because there's less second-guessing (unless the object's naming is equally messy).

- **Sync Custom Shape Position to Bone**. Sync a mesh object's position to each selected bone using it as a custom shape. Made it easier to create custom shapes with better precision. Depends on Rigify being installed.

- **Use Same Custom Shape**. Copies active pose bone's custom shape to each selected pose bone. Any mesh object selected will be the custom shape, effectively assigning it to all selected objects.
