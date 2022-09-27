import bpy
import ifcopenshell
import blenderbim.core.tool
import blenderbim.tool as tool
import blenderbim.core.type


@property
def not_implemented_field(self):
    raise NotImplementedError


class BaseConstrTypeGenerator:
    obj = not_implemented_field
    element = not_implemented_field
    material = not_implemented_field
    collection = not_implemented_field
    collection_obj = not_implemented_field
    location = not_implemented_field
    relating_type_entity = not_implemented_field
    instance_class = not_implemented_field

    def generate_typical_constr_type(self, context, should_add_representation=True):
        self.generate_obj(context)
        self.assign_ifc_class(should_add_representation=should_add_representation)
        self.assign_type()

    def generate_obj(self, context):
        bpy.ops.mesh.primitive_cube_add(location=self.location)
        self.obj = context.active_object
        self.obj.name = tool.Model.generate_occurrence_name(self.relating_type_entity, self.instance_class)

        self.collection = context.view_layer.active_layer_collection.collection
        self.collection.objects.link(self.obj)
        self.collection_obj = bpy.data.objects.get(self.collection.name)

    def assign_ifc_class(self, should_add_representation=True):
        bpy.ops.bim.assign_class(
            obj=self.obj.name, ifc_class=self.instance_class,
            should_add_representation=should_add_representation
        )

    def assign_type(self):
        self.element = tool.Ifc.get_entity(self.obj)
        blenderbim.core.type.assign_type(tool.Ifc, tool.Type, element=self.element,
                                         type=self.relating_type_entity)

        # Update required as core.type.assign_type may change obj.data
        bpy.context.view_layer.update()

    def get_material(self):
        self.material = ifcopenshell.util.element.get_material(self.relating_type_entity)