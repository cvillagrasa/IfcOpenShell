# BlenderBIM Add-on - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021 Dion Moult <dion@thinkmoult.com>
#
# This file is part of BlenderBIM Add-on.
#
# BlenderBIM Add-on is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BlenderBIM Add-on is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BlenderBIM Add-on.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import mathutils
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.system
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.representation
import blenderbim.tool as tool
import blenderbim.core.model as core
import blenderbim.core.type
import blenderbim.core.geometry
from . import wall, slab, profile, mep
from blenderbim.bim.ifc import IfcStore
from blenderbim.bim.module.model.data import AuthoringData
from blenderbim.bim.module.model.base import BaseConstrTypeGenerator
from mathutils import Vector, Matrix
from bpy_extras.object_utils import AddObjectHelper
import warnings


class AddEmptyType(bpy.types.Operator, AddObjectHelper):
    bl_idname = "bim.add_empty_type"
    bl_label = "Add Empty Type"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = bpy.data.objects.new("TYPEX", None)
        context.scene.collection.objects.link(obj)
        context.scene.BIMRootProperties.ifc_product = "IfcElementType"
        bpy.ops.object.select_all(action="DESELECT")
        context.view_layer.objects.active = obj
        obj.select_set(True)
        return {"FINISHED"}


def add_empty_type_button(self, context):
    self.layout.operator(AddEmptyType.bl_idname, icon="FILE_3D")


class AddConstrTypeInstance(bpy.types.Operator, tool.Ifc.Operator, BaseConstrTypeGenerator):
    bl_idname = "bim.add_constr_type_instance"
    bl_label = "Add"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Add Type Instance to the model"
    ifc_class: bpy.props.StringProperty()
    relating_type_id: bpy.props.IntProperty()
    from_invoke: bpy.props.BoolProperty(default=False)
    obj = None
    element = None
    building_obj = None
    building_element = None
    collection = None
    collection_obj = None
    location = None
    props = None
    file = None
    instance_class = None
    relating_type_entity = None
    material = None

    def invoke(self, context, event):
        return self.execute(context)

    def _execute(self, context):
        if flag := self.init_params() is not None:
            return flag

        return self.generate_object(context)

    def init_params(self):
        self.props = bpy.context.scene.BIMModelProperties
        self.file = IfcStore.get_file()
        if self.ifc_class == '':
            self.ifc_class = self.props.ifc_class
        if self.relating_type_id == 0:
            self.relating_type_id = int(self.props.relating_type_id)

        if not self.ifc_class or not self.relating_type_id:
            return {"FINISHED"}

        if self.from_invoke:
            self.props.ifc_class = self.ifc_class
            self.props.relating_type_id = str(self.relating_type_id)

        self.instance_class = ifcopenshell.util.type.get_applicable_entities(
            self.ifc_class, self.file.schema
        )[0]
        self.relating_type_entity = self.file.by_id(self.relating_type_id)
        self.material = ifcopenshell.util.element.get_material(self.relating_type_entity)

        self.building_obj, self.building_element = None, None
        self.location = (0., 0., 0.)

    def generate_object(self, context):
        if self.material and self.material.is_a("IfcMaterialProfileSet"):
            if core.generate_dumb_profile(tool.Model, self.relating_type_entity):
                return {"FINISHED"}
        elif self.material and self.material.is_a("IfcMaterialLayerSet"):
            if core.generate_layered_element(tool.Model, self.ifc_class, self.relating_type_entity):
                return {"FINISHED"}
        if self.relating_type_entity.is_a("IfcFlowSegmentType") and not self.relating_type_entity.RepresentationMaps:
            if core.generate_mep_element(tool.Model, self.relating_type_entity):
                return {"FINISHED"}
        return self.generate_other(context)

    def generate_other(self, context):
        if len(context.selected_objects) == 1 and context.active_object:
            self.building_obj = context.active_object
            self.building_element = tool.Ifc.get_entity(self.building_obj)

        self.generate_typical_constr_type(context, should_add_representation=True)
        self.setup_openings()
        self.create_ports()

        bpy.ops.object.select_all(action="DESELECT")
        self.obj.select_set(True)
        context.view_layer.objects.active = self.obj
        return {"FINISHED"}

    def create_ports(self):
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(tool.Ifc.get())
        for port in ifcopenshell.util.system.get_ports(self.relating_type):
            mat = ifcopenshell.util.placement.get_local_placement(port.ObjectPlacement)
            mat[0][3] *= unit_scale
            mat[1][3] *= unit_scale
            mat[2][3] *= unit_scale
            mat = self.obj.matrix_world @ mathutils.Matrix(mat)
            new_port = tool.Ifc.run("root.create_entity", ifc_class="IfcDistributionPort")
            tool.Ifc.run("system.assign_port", element=self.element, port=new_port)
            tool.Ifc.run("geometry.edit_object_placement", product=new_port, matrix=mat, is_si=True)

    def setup_openings(self):
        voidable_ifc_classes = ["IfcBuiltElement", "IfcBuildingElement"]
        if self.building_obj and self.building_element and any(
                [self.building_element.is_a(ifc_class) for ifc_class in voidable_ifc_classes]):
            self.add_opening()
        elif self.collection_obj and self.collection_obj.BIMObjectProperties.ifc_definition_id:
            self.set_height_from_voided_obj()

    def add_opening(self):
        if self.element.is_a("IfcElement"):
            if self.instance_class not in ["IfcWindow", "IfcDoor"]:
                warnings.warn(f"{self.instance_class} is being used as a voiding element")
            bpy.ops.bim.add_element_opening(
                voided_building_element=self.building_obj.name, filling_building_element=self.obj.name
            )
        if self.instance_class == "IfcDoor":
            self.set_height_from_voided_obj()

    def set_height_from_voided_obj(self):
        self.obj.location[2] = self.building_obj.location[2] - min([v[2] for v in self.obj.bound_box])

    @staticmethod
    def new_cube_mesh(size=2.):
        coords = [-size / 2, +size / 2]
        verts = [Vector(tuple([i, j, k])) for i in coords for j in coords for k in coords]
        edges = []
        faces = [
            [0, 1, 3, 2],
            [2, 3, 7, 6],
            [6, 7, 5, 4],
            [4, 5, 1, 0],
            [2, 6, 4, 0],
            [7, 3, 1, 5],
        ]
        mesh = bpy.data.meshes.new(name="Instance")
        mesh.from_pydata(verts, edges, faces)
        return mesh


class DisplayConstrTypes(bpy.types.Operator):
    bl_idname = "bim.display_constr_types"
    bl_label = "Browse Construction Types"
    bl_options = {"REGISTER"}
    bl_description = "Display all available Construction Types to add new instances"

    def invoke(self, context, event):
        if not AuthoringData.is_loaded:
            AuthoringData.load()
        props = context.scene.BIMModelProperties
        ifc_class = props.ifc_class
        constr_class = core.get_constr_class_info(tool.Model, ifc_class)
        if constr_class is None or not constr_class.fully_loaded:
            core.assetize_constr_class(tool.Model, ifc_class)
        bpy.ops.bim.display_constr_types_ui("INVOKE_DEFAULT")
        return {"FINISHED"}


class AlignProduct(bpy.types.Operator):
    bl_idname = "bim.align_product"
    bl_label = "Align Product"
    bl_options = {"REGISTER", "UNDO"}
    align_type: bpy.props.StringProperty()

    def execute(self, context):
        selected_objs = context.selected_objects
        if len(selected_objs) < 2 or not context.active_object:
            return {"FINISHED"}
        if self.align_type == "CENTERLINE":
            point = context.active_object.matrix_world @ (
                Vector(context.active_object.bound_box[0]) + (context.active_object.dimensions / 2)
            )
        elif self.align_type == "POSITIVE":
            point = context.active_object.matrix_world @ Vector(context.active_object.bound_box[6])
        elif self.align_type == "NEGATIVE":
            point = context.active_object.matrix_world @ Vector(context.active_object.bound_box[0])

        active_x_axis = context.active_object.matrix_world.to_quaternion() @ Vector((1, 0, 0))
        active_y_axis = context.active_object.matrix_world.to_quaternion() @ Vector((0, 1, 0))
        active_z_axis = context.active_object.matrix_world.to_quaternion() @ Vector((0, 0, 1))

        x_distances = self.get_axis_distances(point, active_x_axis, context)
        y_distances = self.get_axis_distances(point, active_y_axis, context)
        if abs(sum(x_distances)) < abs(sum(y_distances)):
            for i, obj in enumerate(selected_objs):
                obj.matrix_world = Matrix.Translation(active_x_axis * -x_distances[i]) @ obj.matrix_world
        else:
            for i, obj in enumerate(selected_objs):
                obj.matrix_world = Matrix.Translation(active_y_axis * -y_distances[i]) @ obj.matrix_world
        return {"FINISHED"}

    def get_axis_distances(self, point, axis, context):
        results = []
        for obj in context.selected_objects:
            if self.align_type == "CENTERLINE":
                obj_point = obj.matrix_world @ (Vector(obj.bound_box[0]) + (obj.dimensions / 2))
            elif self.align_type == "POSITIVE":
                obj_point = obj.matrix_world @ Vector(obj.bound_box[6])
            elif self.align_type == "NEGATIVE":
                obj_point = obj.matrix_world @ Vector(obj.bound_box[0])
            results.append(mathutils.geometry.distance_point_to_plane(obj_point, point, axis))
        return results


class DynamicallyVoidProduct(bpy.types.Operator):
    bl_idname = "bim.dynamically_void_product"
    bl_label = "Dynamically Void Product"
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return IfcStore.get_file()

    def execute(self, context):
        obj = bpy.data.objects.get(self.obj)
        if obj is None:
            return {"FINISHED"}
        product = IfcStore.get_file().by_id(obj.BIMObjectProperties.ifc_definition_id)
        if not product.HasOpenings:
            return {"FINISHED"}
        if [m for m in obj.modifiers if m.type == "BOOLEAN"]:
            return {"FINISHED"}
        representation = ifcopenshell.util.representation.get_representation(product, "Model", "Body", "MODEL_VIEW")
        if not representation:
            return {"FINISHED"}
        was_edit_mode = obj.mode == "EDIT"
        if was_edit_mode:
            bpy.ops.object.mode_set(mode="OBJECT")
        blenderbim.core.geometry.switch_representation(
            tool.Geometry,
            obj=obj,
            representation=representation,
            should_reload=True,
            enable_dynamic_voids=True,
            is_global=True,
            should_sync_changes_first=False,
        )
        if was_edit_mode:
            bpy.ops.object.mode_set(mode="EDIT")
        return {"FINISHED"}
