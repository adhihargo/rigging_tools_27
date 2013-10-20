ADH Rigging Tools
=================

A collection of Blender operators for my personal rigging needs:

- **Rename Regex**. Renames selected objects or bones using regular expressions. Depends on re, standard library module. It's still rough on the edges, but perfectly usable.

### Modifier ###

- **Add Subdivision Surface Modifier**. Adds subdivision surface modifier for all selected objects (except if one is already added), and gives control to their visibility. Should've been named "Add/Toggle..." but that's too unwieldy.

- **Apply Lattices**. Applies all lattice modifiers, and deletes all shapekeys. I use it for lattice-initialized shapekey creation, which for me is much faster and cleaner than plain editing and sculpting.

- **Mask Selected Vertices**. Add a Mask modifier to active mesh object, then assign selected vertices to the vertex group used as mask in the modifier. Modifier alters behavior: Shift-LMB removes selected vertices from mask vertex group, and Ctrl-LMB inverts the vertex group. Works either in Edit mode or otherwise.

- **Delete Mask**. Delete mask created by *Mask Selected Vertices* and its vertex group.

### Custom Shape ###

- **Copy Custom Shapes**. Copies custom shape from one armature to another (on bones with similar name). Sometimes, without knowing the cause, all custom shapes in an armature already well-fit to a character just vanishes. Gone. And it's bloody annoying to reattach them one by one, thus this operator.

- **Use Same Custom Shape**. Copies active pose bone's custom shape to each selected pose bone. Any mesh object selected will be the custom shape, effectively assigning it to all selected objects.

- **Create Custom Shape**. Creates new custom shape object and automatically assigns it to all selected bones. Active bone's name will become the new object's base name. We can:
  - Choose among several simple predefined shapes,
  - Set the object name's prefix,
  - Set the object's size, rotation, position (along the length of bone), and scene layer.

- **Select Custom Shape**. Select active bone's custom shape object, if any. If the shape's scene layers are turned off, one is turned on. If the shape is hidden, it's made visible.

### Bone ###

- **Create Hooks**. This tool has two different behaviors:
  - If an armature object is active, create parentless bone for each selected bone and bind both with Copy Transform constraint (local-to-local coordinate mapping).
  - If a lattice object is active and there's an armature also selected, create bones at each selected lattice point's coordinate and bind it to the point with Hook modifier.

- **Create Spokes**. I use this to setup things like wing feathers and flexible cartoony eyelid. This tool has two different behaviors:
  - If a mesh object is active in Edit mode and there's an armature also selected, create bones emanating from 3D cursor and ending at each selected vertices. Optionally create one parent for *all* newly created bones, and one damped-track tip for each.
  - If an armature is active in Edit or Pose mode, optionally create one parent and one damped-track tip for each selected bones.
  NOTE: Damped Track constrain creation won't be cancelled by Undo operation when in armature Edit mode, so must be removed manually.

- **Create Bone Group**. Creates a new bone group, named after active bone and consisting of all selected bones. Color theme randomly selected among preset themes. If a bone group with the same name already exist, it only changes the existing bone group's color theme.

- **Remove Vertex Groups of Unselected Bones**. In all selected mesh objects, this operator removes all vertex groups other than selected bones. Armature object must be active, in pose mode. I use it right after automatic weight assignment, to remove unwanted bone influence. This makes skinning much faster without sacrificing quality.

- **Bind to Bone**. Binds all selected objects to selected bone, adding armature and vertex group if none exist yet. Compared to just parenting objects to the bone, this is faster while still lets us add component of the object that's controlled by another bone.

### Sync ###

- **Sync Object Data Name To Object**. Sync an object data's name to the object's. Made it easier to reuse object data among separate files because there's less second-guessing (unless the object's naming is equally messy).

- **Sync Custom Shape Position to Bone**. Sync a mesh object's position to each selected bone using it as a custom shape. Made it easier to create custom shapes with better precision. Depends on Rigify being installed.

### Driver ###

- **Copy Driver Settings**. Works only for active object, in Graph Editor - Driver editing mode. Copies all driver type, expression and variables from the topmost selected channel to all other selected channels, for easier manipulation of large amounts of driver.

  There is a textfield above this operator's button that specifies increment/decrement amount for each integer in the expression script. For example, filling this textfield with "1+1 2-10" means increase each 1st integer in expression by one, and decrease each 2nd integer by ten (`(var * 2) + 20` turns to `(var * 3) + 10`, `(var * 4) + 0`, etc. at each copying).
