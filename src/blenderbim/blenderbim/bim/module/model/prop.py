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
from blenderbim.bim.module.model.data import AuthoringData
from bpy.types import PropertyGroup
import blenderbim.core.model as core
import blenderbim.tool as tool
from blenderbim.bim.module.model.handler import ConstrTypeEntityNotFound


def get_ifc_classes(self, context):
    if not AuthoringData.is_loaded:
        AuthoringData.load()
    return [(ifc_class, ifc_class, "") for ifc_class in AuthoringData.data["constr_classes"]]


def get_relating_types(self, context):
    if not AuthoringData.is_loaded:
        AuthoringData.load()
    return [
        (str(entity.id()), entity.Name, entity.Description or "")
        for entity in AuthoringData.data["constr_entities"]
    ]


def get_relating_types_browser(self, context):
    if not AuthoringData.is_loaded:
        AuthoringData.load()
    return [
        (str(entity.id()), entity.Name, entity.Description or "")
        for entity in AuthoringData.data["constr_entities_browser"]
    ]


def update_icon_id(self, context, from_browser=False):
    ifc_class = self.ifc_class_browser if from_browser else self.ifc_class
    relating_type_id = int(self.relating_type_id_browser if from_browser else self.relating_type_id)
    relating_type = core.get_relating_type_name_by_id(tool.Model, ifc_class, relating_type_id)

    if ifc_class not in self.constr_classes or relating_type not in self.constr_classes[ifc_class].constr_types:
        try:
            core.assetize_active_constr_type(tool.Model, from_browser=from_browser)
        except ConstrTypeEntityNotFound:
            return
    self.icon_id = self.constr_classes[ifc_class].constr_types[relating_type].icon_id


def update_ifc_class(self, context):
    AuthoringData.load_constr_classes()
    AuthoringData.load_constr_entities()
    if not self.updating:
        update_icon_id(self, context)


def update_ifc_class_browser(self, context):
    AuthoringData.load_constr_classes()
    AuthoringData.load_constr_entities_browser()
    if self.updating:
        return
    ifc_class = self.ifc_class_browser
    constr_class_info = core.get_constr_class_info(tool.Model, ifc_class)
    if constr_class_info is None or not constr_class_info.fully_loaded:
        core.assetize_constr_class(tool.Model, ifc_class)


def update_relating_type(self, context):
    AuthoringData.load_constr_entities()
    if not self.updating:
        update_icon_id(self, context)


def update_relating_type_browser(self, context):
    AuthoringData.load_constr_entities_browser()
    if not self.updating:
        update_icon_id(self, context, from_browser=True)


def update_relating_type_by_name(self, context):
    AuthoringData.load_constr_entities()
    relating_type_id = core.get_relating_type_id_by_name(tool.Model, self.ifc_class, self.relating_type)
    if relating_type_id is not None:
        self.relating_type_id = relating_type_id


def update_preview_multiple(self, context):
    if self.preview_multiple_constr_types:
        ifc_class = self.ifc_class
        constr_class_info = core.get_constr_class_info(tool.Model, ifc_class)
        if constr_class_info is None or not constr_class_info.fully_loaded:
            core.assetize_constr_class(tool.Model, ifc_class)
    else:
        update_relating_type(self, context)


class ConstrTypeInfo(PropertyGroup):
    name: bpy.props.StringProperty(name="Construction type")
    icon_id: bpy.props.IntProperty(name="Icon ID")
    object: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)


class ConstrClassInfo(PropertyGroup):
    name: bpy.props.StringProperty(name="Construction class")
    constr_types: bpy.props.CollectionProperty(type=ConstrTypeInfo)
    fully_loaded: bpy.props.BoolProperty(default=False)


class BIMModelProperties(PropertyGroup):
    ifc_class: bpy.props.EnumProperty(items=get_ifc_classes, name="Construction Class", update=update_ifc_class)
    ifc_class_browser: bpy.props.EnumProperty(
        items=get_ifc_classes, name="Construction Class", update=update_ifc_class_browser
    )
    relating_type: bpy.props.StringProperty(update=update_relating_type_by_name)
    relating_type_id: bpy.props.EnumProperty(
        items=get_relating_types, name="Construction Type", update=update_relating_type
    )
    relating_type_id_browser: bpy.props.EnumProperty(
        items=get_relating_types_browser, name="Construction Type", update=update_relating_type_browser
    )
    icon_id: bpy.props.IntProperty()
    preview_multiple_constr_types: bpy.props.BoolProperty(default=False, update=update_preview_multiple)
    updating: bpy.props.BoolProperty(default=False)
    occurrence_name_style: bpy.props.EnumProperty(
        items=[("CLASS", "By Class", ""), ("TYPE", "By Type", ""), ("CUSTOM", "Custom", "")],
        name="Occurrence Name Style",
    )
    occurrence_name_function: bpy.props.StringProperty(name="Occurrence Name Function")
    getter_enum = {"ifc_class": get_ifc_classes, "relating_type": get_relating_types}
    constr_classes: bpy.props.CollectionProperty(type=ConstrClassInfo)
