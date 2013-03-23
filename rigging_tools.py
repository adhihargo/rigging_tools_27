import bpy
import rigify
import re

bl_info = {
    "name": "ADH Rigging Tools",
    "author": "Adhi Hargo",
    "version": (1, 0, 0),
    "blender": (2, 65, 0),
    "location": "View3D > Tools > ADH Rigging Tools",
    "description": "Several simple tools to aid rigging.",
    "warning": "",
    "wiki_url": "https://github.com/adhihargo/rigging_tools",
    "tracker_url": "https://github.com/adhihargo/rigging_tools/issues",
    "category": "Rigging"}

bpy.types.Scene.adh_regex_search_pattern = bpy.props.StringProperty(
    name='',
    description='Regular pattern to match against',
    options={'SKIP_SAVE'})
bpy.types.Scene.adh_regex_replacement_string = bpy.props.StringProperty(
    name='',
    description='String to replace each match',
    options={'SKIP_SAVE'})

class ADH_AddSubdivisionSurfaceModifier(bpy.types.Operator):
    """Add subdivision surface modifier to selected objects, if none given yet."""
    bl_idname = 'object.adh_add_subsurf_modifier'
    bl_label = 'Add Subdivision Surface Modifier'
    bl_options = {'REGISTER', 'UNDO'}

    show_viewport = bpy.props.BoolProperty(
        name = 'Show in Viewport',
        default = False,
        description = "Show Subdivision Surface modifier's effect in viewport"
        )

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'\
            and context.selected_objects != []

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects
                  if obj.type == 'MESH']
        for obj in meshes:
            sml = [m for m in obj.modifiers if m.type == 'SUBSURF']
            if sml == []:
                sm = obj.modifiers.new('Subsurf', 'SUBSURF')
                sm.show_viewport = self.show_viewport
                sm.show_expanded = False
            else:
                for sm in sml:
                    sm.show_viewport = self.show_viewport
                    sm.show_expanded = False

        return {'FINISHED'}

class ADH_ApplyLattices(bpy.types.Operator):
    """Applies all lattice modifiers, deletes all shapekeys. Used for lattice-initialized shapekey creation."""
    bl_idname = 'object.adh_apply_lattices'
    bl_label = 'Apply Lattices'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'\
            and context.selected_objects != []\
            and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        if obj.data.shape_keys:
            for i in range (len(obj.data.shape_keys.key_blocks), 0, -1):
                obj.active_shape_key_index = i - 1
                bpy.ops.object.shape_key_remove()
        for m in obj.modifiers:
            if m.type == 'LATTICE':
                bpy.ops.object.modifier_apply(modifier=m.name)

        return {'FINISHED'}

class ADH_CopyCustomShapes(bpy.types.Operator):
    """Copies custom shapes from one armature to another (on bones with similar name)."""
    bl_idname = 'object.adh_copy_shapes'
    bl_label = 'Copy Custom Shapes'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        non_armatures_selected = [o.type for o in context.selected_objects
                                  if o.type != 'ARMATURE']
        return len(context.selected_objects) >= 2 and not non_armatures_selected

    def execute(self, context):
        src_armature = context.active_object
        dst_armatures = context.selected_objects
        dst_armatures.remove(src_armature)

        for bone in src_armature.pose.bones:
            for armature in dst_armatures:
                try:
                    armature.pose.bones[bone.name].custom_shape =\
                        bone.custom_shape
                except:
                    pass

        return {'FINISHED'}

class ADH_CreateCustomShape(bpy.types.Operator):
    """Creates mesh for custom shape for selected bones, at active bone's position, using its name as suffix."""
    bl_idname = 'object.adh_create_shape'
    bl_label = 'Create Custom Shape'
    bl_options = {'REGISTER', 'UNDO'}

    widget_shape = bpy.props.EnumProperty(
        name = 'Widget Shape',
        items = [('sphere', 'Sphere', 'Sphere (8x4 vertices)'),
                 ('ring', 'Ring', 'Ring (12 vertices)')])

    @classmethod
    def poll(self, context):
        return context.active_object.type == 'ARMATURE'\
            and context.mode == 'POSE'

    def execute(self, context):
        pass

class ADH_CreateHookBones(bpy.types.Operator):
    """Creates parentless bone for each selected bone, local copy-transformed. Used for lattice deformation."""
    bl_idname = 'object.adh_create_hook_bones'
    bl_label = 'Create Hook Bones'
    bl_options = {'REGISTER', 'UNDO'}

    hook_layers = bpy.props.BoolVectorProperty(
        name = "Hook Layers",
        description = "Armature layers where new hooks will be placed",
        subtype = 'LAYER',
        size = 32,
        default = (False, False, False, False, False, False, False, False,
                   False, False, False, False, False, False, False, False,
                   False, False, False, False, False, False, False, False,
                   False, False, False, False, False, False, True , False)
        )

    @classmethod
    def poll(self, context):
        return context.active_object.type == 'ARMATURE'

    def execute(self, context):
        prev_mode = 'EDIT' if context.mode == 'EDIT_ARMATURE' else context.mode
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in context.selected_bones:
            hook_name = 'hook-%s' % bone.name
            hook = context.active_object.data.edit_bones.new(hook_name)
            hook.head = bone.head
            hook.tail = bone.tail
            hook.bbone_x = bone.bbone_x / 2
            hook.bbone_z = bone.bbone_z / 2
            hook.layers = self.hook_layers
            hook.roll = bone.roll
        bpy.ops.object.mode_set(mode='POSE')
        for bone in context.selected_pose_bones:
            hook = context.active_object.pose.bones['hook-%s' % bone.name]
            ct_constraint = hook.constraints.new('COPY_TRANSFORMS')
            ct_constraint.owner_space = 'LOCAL'
            ct_constraint.target_space = 'LOCAL'
            ct_constraint.target = context.active_object
            ct_constraint.subtarget = bone.name
        bpy.ops.object.mode_set(mode=prev_mode)

        return {'FINISHED'}

class ADH_DisplayWireForSkinnedObjects(bpy.types.Operator):
    """Used to ease bone placement."""
    bl_idname = 'object.adh_display_wire_if_skinned' # Ugly name, sorry.
    bl_label = 'Display Wire For Skinned Objects'
    bl_options = {'REGISTER', 'UNDO'}

    show_wire = bpy.props.BoolProperty(
        name = 'Show Wire',
        default = False,
        description = 'Toggle show wire for all objects using selected armature'
        )

    @classmethod
    def poll(self, context):
        return context.active_object \
            and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        armature_obj = context.active_object
        affected_objects = []
        
        for obj in context.selectable_objects:
            armature_mod = [m for m in obj.modifiers if
                            m.type == 'ARMATURE' and
                            m.object == armature_obj]
            if armature_mod:
                affected_objects.append(obj)
        
        for obj in affected_objects:
            obj.show_wire = self.show_wire

        return {'FINISHED'}

class ADH_RemoveVertexGroupsUnselectedBones(bpy.types.Operator):
    """Removes all vertex groups other than selected bones.

    Used right after automatic weight assignment, to remove unwanted bone influence."""
    bl_idname = 'object.adh_remove_vertex_groups_unselected_bones'
    bl_label = 'Remove Vertex Groups of Unselected Bones'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.selected_pose_bones != None

    def execute(self, context):
        bone_names = [b.name for b in context.selected_pose_bones]
        affected_objects = [o for o in context.selected_objects
                            if o.type == 'MESH']
        
        for obj in affected_objects:
            for vg in obj.vertex_groups:
                if not vg.name in bone_names:
                    obj.vertex_groups.remove(vg)

        return {'FINISHED'}

class ADH_RenameRegex(bpy.types.Operator):
    """Renames selected objects or bones using regular expressions. Depends on re, standard library module."""
    bl_idname = 'object.adh_rename_regex'
    bl_label = 'Rename Regex'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.selected_objects != []

    def execute(self, context):
        substring_re = re.compile(context.scene.adh_regex_search_pattern)
        if context.mode == 'OBJECT':
            item_list = context.selected_objects
        elif context.mode == 'POSE':
            item_list = context.selected_pose_bones
        elif context.mode == 'EDIT_ARMATURE':
            item_list = context.selected_bones
        else:
            return {'CANCELLED'}

        for item in item_list:
            item.name = substring_re.sub(context.scene.adh_regex_replacement_string,
                                         item.name)

        # In pose mode, operator's result won't show immediately. This
        # solves it somehow: only the View3D area will refresh
        # promptly.
        if context.mode == 'POSE':
            context.area.tag_redraw()

        return {'FINISHED'}

class ADH_SyncObjectDataNameToObject(bpy.types.Operator):
    """Sync an object data's name to the object's. Made it easier to reuse object data among separate files."""
    bl_idname = 'object.adh_sync_data_name_to_object'
    bl_label = 'Sync Object Data Name To Object'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.selected_objects

    def execute(self, context):
        for obj in context.selected_objects:
            if obj and obj.data:
                obj.data.name = obj.name

        return {'FINISHED'}

class ADH_SyncCustomShapePositionToBone(bpy.types.Operator):
    """Sync a mesh object's position to each selected bone using it as a custom shape. Depends on Rigify."""
    bl_idname = 'object.adh_sync_shape_position_to_bone'
    bl_label = 'Sync Custom Shape Position to Bone'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.active_object.type == 'ARMATURE'\
            and context.mode == 'POSE'
    
    def execute(self, context):
        for bone in context.selected_pose_bones:
            obj = bone.custom_shape
            if obj:
                rigify.utils.obj_to_bone(obj, context.active_object,
                                         bone.name)

        return {'FINISHED'}

class ADH_UseSameCustomShape(bpy.types.Operator):
    """Copies active pose bone's custom shape to each selected pose bone."""
    bl_idname = 'object.adh_use_same_shape'
    bl_label = 'Use Same Custom Shape'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.active_pose_bone != None

    def execute(self, context):
        if context.active_pose_bone == None:
            return {'CANCELLED'}

        custom_shape = context.active_pose_bone.custom_shape
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                custom_shape = obj
                break

        for bone in context.selected_pose_bones:
            bone.custom_shape = custom_shape

        return {'FINISHED'}

class ADH_RiggingToolsPanel(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_ADH_rigging_tools'
    bl_label = 'ADH Rigging Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=1)
        col.operator('object.adh_rename_regex')
        col.prop(context.scene, 'adh_regex_search_pattern')
        col.prop(context.scene, 'adh_regex_replacement_string')

        col = layout.column(align=1)
        col.operator('object.adh_add_subsurf_modifier', text='Add Subsurf')
        col.operator('object.adh_apply_lattices')

        col = layout.column(align=1)
        col.operator('object.adh_copy_shapes')
        col.operator('object.adh_use_same_shape')
        col.operator('object.adh_create_shape')

        col = layout.column(align=1)
        col.operator('object.adh_create_hook_bones')
        col.operator('object.adh_display_wire_if_skinned', text='Display Wire')
        col.operator('object.adh_remove_vertex_groups_unselected_bones', text='Remove Unselected VG')

        col = layout.column(align=1)
        col.operator('object.adh_sync_data_name_to_object', text='ObData.name <- Ob.name')
        col.operator('object.adh_sync_shape_position_to_bone', text='CustShape.pos <- Bone.pos')

def register():
    bpy.utils.register_module(__name__)
    
def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
