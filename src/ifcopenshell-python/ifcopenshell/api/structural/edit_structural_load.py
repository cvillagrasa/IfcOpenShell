# IfcOpenShell - IFC toolkit and geometry engine
# Copyright (C) 2021 Dion Moult <dion@thinkmoult.com>
#
# This file is part of IfcOpenShell.
#
# IfcOpenShell is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# IfcOpenShell is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with IfcOpenShell.  If not, see <http://www.gnu.org/licenses/>.


def edit_structural_load(file, structural_load=None, attributes=None) -> None:
    """Edits the attributes of an IfcStructuralLoad

    For more information about the attributes and data types of an
    IfcStructuralLoad, consult the IFC documentation.

    :param structural_load: The IfcStructuralLoad entity you want to edit
    :type structural_load: ifcopenshell.entity_instance
    :param attributes: a dictionary of attribute names and values.
    :type attributes: dict, optional
    :return: None
    :rtype: None
    """
    settings = {"structural_load": structural_load, "attributes": attributes or {}}

    for name, value in settings["attributes"].items():
        setattr(settings["structural_load"], name, value)
