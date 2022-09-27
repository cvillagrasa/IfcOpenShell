# BlenderBIM Add-on - OpenBIM Blender Add-on
# Copyright (C) 2022 Dion Moult <dion@thinkmoult.com>
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
import ifcopenshell
import blenderbim.core.type
import blenderbim.tool as tool
from blenderbim.bim.module.model.handler import ConstrTypeEntityNotFound
from blenderbim.bim.module.model.profile import DumbProfileGenerator
from blenderbim.bim.module.model.wall import DumbWallGenerator
from blenderbim.bim.module.model.slab import DumbSlabGenerator
from blenderbim.bim.module.model.mep import MepGenerator
import warnings


class Model(blenderbim.core.tool.Model):
    @classmethod
    def generate_occurrence_name(cls, element_type_entity, ifc_class):
        props = bpy.context.scene.BIMModelProperties
        if props.occurrence_name_style == "CLASS":
            return ifc_class[3:]
        elif props.occurrence_name_style == "TYPE":
            return element_type_entity.Name or "Unnamed"
        elif props.occurrence_name_style == "CUSTOM":
            try:
                # Power users gonna power
                return eval(props.occurrence_name_function) or "Instance"
            except:
                return "Instance"

    @classmethod
    def get_active_constr_class(cls):
        return bpy.context.scene.BIMModelProperties.ifc_class

    @classmethod
    def get_active_relating_type_id(cls):
        return bpy.context.scene.BIMModelProperties.relating_type_id

    @classmethod
    def get_ifc_class_entities(cls, ifc_class):
        return sorted(tool.Ifc.get().by_type(ifc_class), key=lambda s: s.Name)

    @classmethod
    def get_relating_type_name_by_id(cls, ifc_class, relating_type_id):
        try:
            constr_class_entity = tool.Ifc.get().by_id(relating_type_id)
        except (RuntimeError, ValueError):
            warnings.warn(f"Relating type ID {relating_type_id} could not be found")
            return None
        if not constr_class_entity.is_a(ifc_class):
            warnings.warn(f"Relating type ID {relating_type_id} is a {constr_class_entity.is_a()}, not a {ifc_class}")
        return constr_class_entity.Name

    @classmethod
    def get_relating_type_id_by_name(cls, ifc_class, relating_type):
        relating_type_ids = [e.id() for e in cls.get_ifc_class_entities(ifc_class) if e.Name == relating_type]
        return None if len(relating_type_ids) == 0 else relating_type_ids[0]

    @staticmethod
    def new_constr_class_info(ifc_class):
        props = bpy.context.scene.BIMModelProperties
        if ifc_class not in props.constr_classes:
            props.constr_classes.add().name = ifc_class
        return props.constr_classes[ifc_class]

    @staticmethod
    def get_constr_class_info(ifc_class):
        props = bpy.context.scene.BIMModelProperties
        return props.constr_classes[ifc_class] if ifc_class in props.constr_classes else None

    @classmethod
    def updating_transaction(cls, restore_selection=True):
        props = bpy.context.scene.BIMModelProperties

        class ContextManager:
            def __init__(self):
                self.active_ifc_class = props.ifc_class
                self.active_relating_type_id = props.relating_type_id

            def __enter__(self):
                props.updating = True

            def __exit__(self, exc_type, exc_val, exc_tb):
                if restore_selection:
                    props.ifc_class = self.active_ifc_class
                    props.relating_type_id = self.active_relating_type_id
                props.updating = False

        return ContextManager()

    @classmethod
    def generate_layered_element(cls, ifc_class, relating_type_entity):
        layer_set_direction = None
        parametric = ifcopenshell.util.element.get_psets(relating_type_entity).get("EPset_Parametric")
        if parametric:
            layer_set_direction = parametric.get("LayerSetDirection", layer_set_direction)
        if layer_set_direction is None:
            if ifc_class in ["IfcSlabType", "IfcRoofType", "IfcRampType", "IfcPlateType"]:
                layer_set_direction = "AXIS3"
            else:
                layer_set_direction = "AXIS2"

        if layer_set_direction == "AXIS3":
            if DumbSlabGenerator(relating_type_entity).generate():
                return True
        elif layer_set_direction == "AXIS2":
            if DumbWallGenerator(relating_type_entity).generate():
                return True
        else:
            pass  # Dumb block generator? Eh? :)

    @classmethod
    def generate_mep_element(cls, relating_type_entity):
        return MepGenerator(relating_type_entity).generate()

    @classmethod
    def generate_dumb_profile(cls, relating_type_entity):
        return DumbProfileGenerator(relating_type_entity).generate()

    @classmethod
    def generate_element_other(cls):
        pass

    @classmethod
    def new_constr_type_instance(cls, ifc_class, relating_type_id):
        props = bpy.context.scene.BIMModelProperties

        with cls.updating_transaction(restore_selection=False):
            props.ifc_class = ifc_class
            props.relating_type_id = str(relating_type_id)

        bpy.ops.bim.add_constr_type_instance()   ### avoid call to operator
        return bpy.context.selected_objects[-1]

    @classmethod
    def remove_constr_type_object(cls, obj):
        element = tool.Ifc.get_entity(obj)
        if element:
            tool.Ifc.delete(element)
        tool.Ifc.unlink(obj=obj)
        for collection in obj.users_collection:
            collection.objects.unlink(obj)

    @classmethod
    def assetize_object(cls, obj, ifc_class, relating_type_id):
        props = bpy.context.scene.BIMModelProperties
        to_be_deleted = False

        if obj.type == "EMPTY":
            if new_obj := cls.new_constr_type_instance(ifc_class, relating_type_id) is not None:
                to_be_deleted = True
                obj = new_obj
        obj.asset_mark()
        obj.asset_generate_preview()

        if ifc_class not in props.constr_classes:
            props.constr_classes.add().name = ifc_class
        info = props.constr_classes[ifc_class]

        relating_type = cls.get_relating_type_name_by_id(relating_type_id)
        if relating_type not in info.constr_types:
            info.constr_types.add().name = relating_type
        rtype = info.constr_types[relating_type]
        rtype.object = obj
        rtype.icon_id = obj.preview.icon_id

        if to_be_deleted:
            cls.remove_constr_type_object(obj)

    @classmethod
    def assetize_constr_class(cls, ifc_class):
        props = bpy.context.scene.BIMModelProperties
        with cls.updating_transaction():
            constr_class = cls.get_constr_class_info(ifc_class)
            _ = cls.new_constr_class_info(ifc_class) if constr_class is None else constr_class
            constr_class_occurrences = cls.get_ifc_class_entities(ifc_class)
            constr_classes = props.constr_classes

            for constr_class_entity in constr_class_occurrences:
                if (
                    ifc_class not in constr_classes
                    or constr_class_entity.Name not in constr_classes[ifc_class].constr_types
                ):
                    obj = tool.Ifc.get_object(constr_class_entity)
                    cls.assetize_object(obj, ifc_class, constr_class_entity.id())
            cls.get_constr_class_info(ifc_class).fully_loaded = True

    @classmethod
    def assetize_active_constr_type(cls, from_browser=False):
        props = bpy.context.scene.BIMModelProperties
        ifc_class = props.ifc_class_browser if from_browser else props.ifc_class
        relating_type_id = props.relating_type_id_browser if from_browser else props.relating_type_id

        constr_entities = cls.get_ifc_class_entities(ifc_class)
        constr_entities = [entity for entity in constr_entities if entity.id() == relating_type_id]

        if len(constr_entities) == 0:
            raise ConstrTypeEntityNotFound()

        constr_entity = constr_entities[0]
        if obj := tool.Ifc.get_object(constr_entity) is None:
            raise ConstrTypeEntityNotFound()

        cls.assetize_object(obj, props.ifc_class, constr_entity.id())
