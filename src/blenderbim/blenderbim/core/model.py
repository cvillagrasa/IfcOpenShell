import bpy
from typing import Optional


class ConstrClassInfo:
    pass  # dummy typing class for readability only


class Model:
    pass  # dummy typing class for readability only


class entity_instance:
    pass  # dummy typing class for readability only


def get_active_constr_class(model: Model) -> str:
    return model.get_active_constr_class()


def get_active_relating_type_id(model: Model) -> int:
    return model.get_active_relating_type_id()


def get_ifc_class_entities(model: Model, ifc_class: str) -> list[str]:
    return model.get_ifc_class_entities(ifc_class)


def get_relating_type_name_by_id(model: Model, ifc_class: str, relating_type_id: int) -> str:
    return model.get_relating_type_name_by_id(ifc_class, relating_type_id)


def get_relating_type_id_by_name(model: Model, ifc_class: str, relating_type: str) -> int:
    return model.get_relating_type_id_by_name(ifc_class, relating_type)


def new_constr_class_info(model: Model, ifc_class: str) -> ConstrClassInfo:
    return model.new_constr_class_info(ifc_class)


def get_constr_class_info(model: Model, ifc_class: str) -> Optional[ConstrClassInfo]:
    return model.get_constr_class_info(ifc_class)


def generate_layered_element(model: Model, ifc_class: str, relating_type_entity: entity_instance) -> Optional[bool]:
    return model.generate_layered_element(ifc_class, relating_type_entity)


def generate_dumb_profile(model: Model, relating_type_entity: entity_instance) -> Optional[bpy.types.Object]:
    return model.generate_dumb_profile(relating_type_entity)


def generate_mep_element(model: Model, relating_type_entity: entity_instance) -> Optional[bpy.types.Object]:
    return model.generate_mep_element(relating_type_entity)


def new_constr_type_instance(model: Model, ifc_class: str, relating_type_id: int) -> bpy.types.Object:
    return model.new_constr_type_instance(ifc_class, relating_type_id)


def remove_constr_type_object(model: Model, obj: bpy.types.Object) -> None:
    return model.remove_constr_type_object(obj)


def assetize_object(model: Model, obj: bpy.types.Object, ifc_class: str, relating_type_id: int) -> None:
    return model.assetize_object(obj, ifc_class, relating_type_id)


def assetize_constr_class(model: Model, ifc_class: str) -> None:
    return model.assetize_constr_class(ifc_class)


def assetize_active_constr_type(model: Model, from_browser: bool = False) -> None:
    return model.assetize_active_constr_type(from_browser=from_browser)
