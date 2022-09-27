import blenderbim
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.system
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.representation
import blenderbim.tool as tool
import blenderbim.core.type
import blenderbim.core.geometry
from blenderbim.bim.ifc import IfcStore


def generate_box(usecase_path, ifc_file, settings):
    box_context = ifcopenshell.util.representation.get_context(ifc_file, "Model", "Box", "MODEL_VIEW")
    if not box_context:
        return
    obj = settings["blender_object"]
    if 0 in list(obj.dimensions):
        return
    product = ifc_file.by_id(obj.BIMObjectProperties.ifc_definition_id)
    old_box = ifcopenshell.util.representation.get_representation(product, "Model", "Box", "MODEL_VIEW")
    if settings["context"].ContextType == "Model" and getattr(settings["context"], "ContextIdentifier") == "Body":
        if old_box:
            blenderbim.core.geometry.remove_representation(tool.Ifc, tool.Geometry, obj=obj, representation=old_box)

        new_settings = settings.copy()
        new_settings["context"] = box_context
        new_box = ifcopenshell.api.run(
            "geometry.add_representation", ifc_file, should_run_listeners=False, **new_settings
        )
        ifcopenshell.api.run(
            "geometry.assign_representation",
            ifc_file,
            should_run_listeners=False,
            **{"product": product, "representation": new_box}
        )


def regenerate_profile_usage(usecase_path, ifc_file, settings):
    elements = []
    if ifc_file.schema == "IFC2X3":
        for rel in ifc_file.get_inverse(settings["usage"]):
            if not rel.is_a("IfcRelAssociatesMaterial"):
                continue
            for element in rel.RelatedObjects:
                elements.append(element)
    else:
        for rel in settings["usage"].AssociatedTo:
            for element in rel.RelatedObjects:
                elements.append(element)

    for element in elements:
        obj = IfcStore.get_element(element.id())
        if not obj:
            continue
        representation = ifcopenshell.util.representation.get_representation(element, "Model", "Body", "MODEL_VIEW")
        if representation:
            blenderbim.core.geometry.switch_representation(
                tool.Geometry,
                obj=obj,
                representation=representation,
                should_reload=True,
                enable_dynamic_voids=True,
                is_global=True,
                should_sync_changes_first=False,
            )


def ensure_material_assigned(usecase_path, ifc_file, settings):
    if usecase_path == "material.assign_material":
        if not settings.get("material", None):
            return
        elements = [settings["product"]]
    else:
        elements = []
        for rel in ifc_file.by_type("IfcRelAssociatesMaterial"):
            if rel.RelatingMaterial == settings["material"] or [
                e for e in ifc_file.traverse(rel.RelatingMaterial) if e == settings["material"]
            ]:
                elements.extend(rel.RelatedObjects)

    for element in elements:
        obj = IfcStore.get_element(element.GlobalId)
        if not obj or not obj.data:
            continue

        element_material = ifcopenshell.util.element.get_material(element)
        material = [m for m in ifc_file.traverse(element_material) if m.is_a("IfcMaterial")]

        object_material_ids = [
            om.BIMObjectProperties.ifc_definition_id
            for om in obj.data.materials
            if om is not None and om.BIMObjectProperties.ifc_definition_id
        ]

        if material and material[0].id() in object_material_ids:
            continue

        if len(obj.data.materials) == 1:
            obj.data.materials.clear()

        if not material:
            continue

        obj.data.materials.append(IfcStore.get_element(material[0].id()))