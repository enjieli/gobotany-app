# -*- coding: utf-8 -*-

import re

from os.path import abspath, dirname

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from lxml import etree

from gobotany.core import models

GRAPHICS_ROOT = abspath(dirname(__file__) + '/../static/graphics')
NAMESPACES = {'svg': 'http://www.w3.org/2000/svg'}
STATES = [k.upper() for k, v in list(settings.STATE_NAMES.items())]

class Path(object):
    """Class for operating on a SVG path node."""
    STYLE_ATTR = 'style'
    FILL_PATTERN = re.compile(r'(.*fill:)#[a-f0-9]{3,6}(;.*|$)')
    STROKE_PATTERN = re.compile(r'(.*stroke:)#[a-f0-9]{3,6}(;.*|$)')

    def __init__(self, path_node):
        self.path_node = path_node

    def get_style(self):
        return self.path_node.get(Path.STYLE_ATTR)

    def set_style(self, value):
        self.path_node.set(Path.STYLE_ATTR, value)

    def color(self, fill_color, stroke_color=None):
        style = self.get_style()
        replacement = r'\1%s\2' % fill_color
        shaded_style = re.sub(Path.FILL_PATTERN, replacement, style)
        if stroke_color:
            replacement = r'\1%s\2' % stroke_color
            shaded_style = re.sub(Path.STROKE_PATTERN, replacement,
                                  shaded_style)
        self.set_style(shaded_style)

    def __str__(self):
        return '%s (%s)' % (self.path_node.get('id'), self.get_style())


class Legend(object):
    """Class for configuring the legend on a SVG plant distribution map."""

    # This list controls the order, label and color of legend items.
    # Purple is used instead of red, partly to avoid problems for those
    # with red-green color blindness.
    # Some items' labels are suffixed with 'nn' for non-native; this is
    # so the COLORS dictionary can have unique keys. This suffix is
    # removed upon display in the legend.
    ITEMS = [('county documented na', '#35880c'), # dark green, county native
        ('state documented na', '#98f25a'),  # light green, state native
        ('native', '#98f25a'),     # light green (for U.S. map)
        ('county documented nn', '#8e54d6'), # dark purple, county non-native
        ('state documented nn', '#c091fa'), # lt. purple, state non-native
        ('non-native', '#c091fa'), # light purple (for U.S. map)
        ('absent', '#fff'),   # absent no longer shown in legend
    ]
    COLORS = dict(ITEMS)  # Color lookup for labels, ex.: COLORS['rare'].
                          # This does not preserve the order of items.

    def __init__(self, svg_map, maximum_categories, maximum_items):
        self.svg_map = svg_map
        self.maximum_categories = maximum_categories
        self.maximum_items = maximum_items

    def _set_category_label(self, category_number, label):
        label_node_id = 'category%s' % str(category_number)
        try:
            label_node = self.svg_map.xpath(
                'svg:text[@id="%s"]' % label_node_id,
                namespaces=NAMESPACES)[0]
            if label_node is not None:
                label_text_node = label_node.find(
                    '{http://www.w3.org/2000/svg}tspan')
                label_text_node.text = label
        except:
            pass

    def _get_item_label(self, slot_number):
        label = ''
        label_node_id = 'label%s' % str(slot_number)
        try:
            label_node = self.svg_map.xpath(
                'svg:text[@id="%s"]' % label_node_id,
                namespaces=NAMESPACES)[0]
            if label_node is not None:
                label_text_node = label_node.find(
                    '{http://www.w3.org/2000/svg}tspan')
                label = label_text_node.text
        except:
            pass
        return label

    def _set_item_label(self, label_node, label):
        # Because SVG does not handle multi-line text easily, first
        # check for multiple lines in the label area and if found,
        # split the label text over the lines. Currently this handles
        # only one word per line (e.g., 2 lines, 2-word labels).
        label_text_nodes = label_node.findall(
            '{http://www.w3.org/2000/svg}tspan')
        lines_available = len(label_text_nodes)
        text_parts = label.split(' ')
        for i in range(lines_available):
            line = label_text_nodes[i]
            if i <= len(text_parts) - 1:
                line.text = text_parts[i]
            else:
                line.text = ''

    def _set_item(self, slot_number, fill_color, stroke_color, item_label):
        box_node_id = 'box%s' % str(slot_number)
        box_node = self.svg_map.xpath('svg:rect[@id="%s"]' % box_node_id,
            namespaces=NAMESPACES)[0]
        box = Path(box_node)
        box.color(fill_color, stroke_color)

        label_node_id = 'label%s' % str(slot_number)
        label_node = self.svg_map.xpath('svg:text[@id="%s"]' % label_node_id,
            namespaces=NAMESPACES)[0]
        self._set_item_label(label_node, item_label)

    def _num_native_labels_found(self, legend_labels_found):
        num_native_found = 0
        for label in legend_labels_found:
            if label.find(' na') > -1:
                num_native_found += 1
        return num_native_found

    def show_items(self, legend_labels_found):
        """Set the colors and labels of the legend items."""

        # For county-level maps, start with category labels hidden.
        for category_number in range(1, self.maximum_categories + 1):
            self._set_category_label(category_number, '')

        for item_slot_number in range(1, self.maximum_items + 1):
            # Only show legend items for data values shown on this map.
            if len(legend_labels_found) >= item_slot_number:
                # Show the legend item.
                label = legend_labels_found[item_slot_number - 1]
                fill_color = Legend.COLORS[label]
                stroke_color = '#fff'   # hide box borders on legend items

                # For county-level maps, set the category labels for
                # the given legend items.
                if label.find(' na') > 1:
                    self._set_category_label(1, 'Native')
                elif label.find(' nn') > 1:
                    category_number = 1
                    if self._num_native_labels_found(legend_labels_found) > 0:
                        category_number = 2
                    self._set_category_label(category_number, 'Non-native')

                # For a non-native label on the county-level map, skip
                # to a second label group if there are also any native
                # labels.
                num_native_labels = self._num_native_labels_found(
                    legend_labels_found)
                if label.find(' nn') > -1 and num_native_labels > 0:
                    item_slot_number += 2 - num_native_labels

                if label.find(' na') > -1 or label.find(' nn') > -1:
                    # Remove any category suffix before label display.
                    label = label[:-3]

                self._set_item(item_slot_number, fill_color, stroke_color,
                    label)

        # If no distribution data were mapped, set a label saying so.
        if len(legend_labels_found) == 0:
            self._set_item(1, '#fff', '#fff', 'no data')

        # Hide any unused boxes.
        for item_slot_number in range(1, self.maximum_items + 1):
            current_label = self._get_item_label(item_slot_number)
            if current_label.find('label') > -1:
                self._set_item(item_slot_number, '#fff', '#fff', '')


class ChloroplethMap(object):
    """Base class for a chloropleth SVG map."""

    def __init__(self, blank_map_path, maximum_legend_items):
        self.svg_map = etree.parse(blank_map_path)
        self.maximum_legend_items = maximum_legend_items

    def _get_title_node(self):
        return self.svg_map.find('{http://www.w3.org/2000/svg}title')

    def get_title(self):
        title = self._get_title_node()
        return title.text

    def set_title(self, value):
        title = self._get_title_node()
        title.text = value

    def tostring(self):
        return etree.tostring(self.svg_map.getroot())


class PlantDistributionMap(ChloroplethMap):
    """Base class for a map that shows plant distribution data."""

    PATH_NODES_XPATH = 'svg:path'

    def __init__(self, blank_map_path):
        self.maximum_legend_categories = 2
        self.maximum_legend_items = 4
        self.scientific_name = None
        super(PlantDistributionMap, self).__init__(blank_map_path,
            self.maximum_legend_items)
        self.legend = Legend(self.svg_map, self.maximum_legend_categories,
            self.maximum_legend_items)

    def _get_label(self, is_present, is_native, level=None):
        """Return the appropriate label for distribution data."""
        label = 'absent'
        if is_present:
            if is_native:
                label = 'native'
            else:
                label = 'non-native'

            if level is not None:
                if level == 'county':
                    label = 'county documented'
                else:
                    label = 'state documented'
                if is_native:
                    label = label + ' na'
                else:
                    label = label + ' nn'
        return label

    def _add_name_to_title(self, scientific_name):
        """Add the plant name to the map's title."""
        title_text = self.get_title()
        sep_index = title_text.find(':')
        if sep_index > -1:
            title_text = title_text[sep_index + 1:].strip()
        title_text = '%s: %s' % (scientific_name, title_text)
        self.set_title(title_text)

    def _get_distribution_records(self, scientific_name):
        """Look up the plant and get its distribution records."""
        return models.Distribution.objects.all_records_for_plant(
            scientific_name)

    def set_plant(self, scientific_name):
        """Set the plant to be shown and gather its data."""
        self.scientific_name = scientific_name
        records = self._get_distribution_records(self.scientific_name)
        if not records:
            # Distribution records might be listed under one of the
            # synonyms for this plant instead.
            try:
                taxon = models.Taxon.objects.get(
                    scientific_name=self.scientific_name)
                if taxon.synonyms:
                    for synonym in taxon.synonyms.all():
                        name = synonym.scientific_name
                        records = self._get_distribution_records(name)
                        if records:
                            break
            except ObjectDoesNotExist:
                pass  # Didn't find the plant in the database
        self.distribution_records = records

        # Only add the plant name to the title if distribution data are
        # found, to keep the title neutral in the event of junk in the URL.
        if records:
            self._add_name_to_title(self.scientific_name)

    def _order_labels(self, labels):
        """Put legend labels in display order."""
        all_labels = [item[0] for item in Legend.ITEMS]
        ordered_labels = [label for label in all_labels if label in labels]
        return ordered_labels

    def _should_shade(self, area, is_present, is_native, level=None):
        should_shade = False
        style = area.get_style()
        shaded_absent = (style.find('fill:%s' % Legend.COLORS['absent']) > 0)
        shaded_non_native = ((style.find(
            'fill:%s' % Legend.COLORS['state documented nn']) > 0) or
            (style.find(
            'fill:%s' % Legend.COLORS['county documented nn']) > 0))
        shaded_state_native = (style.find(
            'fill:%s' % Legend.COLORS['state documented na']) > 0)

        if shaded_absent and is_present:
            # If the area is shaded absent but the new record is
            # present, shade the area.
            should_shade = True
        elif shaded_non_native:
            if is_present:
                if is_native:
                    # If the new record is native, override.
                    should_shade = True
                elif level == 'county':
                    # If the new record is county-level non-native, override.
                    should_shade = True
        elif shaded_state_native:
            # If the new record is county level, override.
            if is_present and level == 'county':
                should_shade = True

        return should_shade

    def _shade_areas(self):
        """Set the colors of the counties or states/provinces based
        on distribution data. Return a list of the legend labels to be
        displayed as a result of this shading.
        """
        legend_labels_found = []
        if self.distribution_records:
            path_nodes = self.svg_map.xpath(self.PATH_NODES_XPATH,
                namespaces=NAMESPACES)

            # When shading a map area, iterate over the nodes rather
            # than selecting a node via XPath. Iterating is around twice
            # as fast as XPath, at least when breaking after finding a node
            # as is done for the county-level records.

            # Take a pass through the nodes and shade any county-level
            # records.
            # Keep track of which states had any county-level records.
            states_with_county_records = []
            county_records = self.distribution_records.exclude(county='')
            for record in county_records:
                state_and_county = '%s_%s' % (record.state.lower(),
                                              record.county.replace(
                                                  ' ', '_').lower())
                for node in path_nodes:
                    node_id = node.get('id').lower()
                    if node_id == state_and_county:
                        label = self._get_label(record.present, record.native,
                            level='county')
                        if label not in legend_labels_found:
                            legend_labels_found.append(label)
                        box = Path(node)
                        if self._should_shade(box, record.present,
                                record.native, level='county'):
                            box.color(Legend.COLORS[label])
                            states_with_county_records.append(
                                record.state.lower())
                        break   # Move on to the next distribution record.

            # Take a pass through the nodes and shade any
            # state-/province-/territory-level records.
            state_records = self.distribution_records.filter(county='')
            for record in state_records:
                state_id_piece = '%s_' % record.state.lower()
                for node in path_nodes:
                    node_id = node.get('id').lower()
                    if node_id.startswith(state_id_piece):
                        # If this state is not one where any county records
                        # were mapped, proceed to map state records.
                        state = record.state.lower()
                        if state not in list(set(states_with_county_records)):
                            label = self._get_label(record.present,
                                record.native, level='state')
                            if label not in legend_labels_found:
                                legend_labels_found.append(label)
                            box = Path(node)
                            if self._should_shade(box, record.present,
                                    record.native):
                                box.color(Legend.COLORS[label])
                            # Keep going rather than break, because for each
                            # state-level record there will be multiple
                            # counties to shade.

            # Check all legend labels found to verify they should still
            # be visible on the map. Drop any labels that no longer have
            # any shaded areas visible on the map due to overrides.
            final_labels = []
            for label in legend_labels_found:
                color = Legend.COLORS[label]
                for node in path_nodes:
                    node_id = node.get('id')
                    if node_id[0:2] in STATES:
                        style = Path(node).get_style()
                        if style.find('fill:%s' % color) > 0:
                            # Found a node with this label's color, so
                            # this label should still be included.
                            final_labels.append(label)
                            break

            legend_labels_found = self._order_labels(final_labels)

            # Omit 'absent' from the items to display in the legend.
            if 'absent' in legend_labels_found:
                legend_labels_found.remove('absent')

        return legend_labels_found

    def shade(self):
        """Shade a New England plant distribution map. Assumes the method
        set_plant(scientific_name) has already been called.
        """
        legend_labels_found = self._shade_areas()
        self.legend.show_items(legend_labels_found)
        return self


class PlantDiversityMap(ChloroplethMap):
    """Base class for a map that shows plant diversity data."""

    PATH_NODES_XPATH = 'svg:path'

    def __init__(self, blank_map_path):
        self.maximum_legend_categories = 1
        self.maximum_legend_items = 7
        self.scientific_name = None
        super(PlantDiversityMap, self).__init__(blank_map_path,
            self.maximum_legend_items)
        self.legend = Legend(self.svg_map, self.maximum_legend_categories,
            self.maximum_legend_items)
        self.map_type = 'all'

    def set_title(self, value):
        super(PlantDiversityMap, self).set_title(value)
        # Set map type based on the title.
        if value.find('non-native') > 0:
            self.map_type = 'nonnative'
        elif value.find('native') > 0:
            self.map_type = 'native'
        # Also set the visible title label on the map.
        label_node_id = 'title'
        try:
            label_node = self.svg_map.xpath(
                'svg:text[@id="%s"]' % label_node_id,
                namespaces=NAMESPACES)[0]
            if label_node is not None:
                label_text_node = label_node.find(
                    '{http://www.w3.org/2000/svg}tspan')
                label_text_node.text = value
        except:
            pass

    def set_data(self, data):
        self.data = data

    def _get_color(self, taxa_count):
        color = 'fff'
        if self.map_type == 'native':
            if taxa_count > 475 and taxa_count <= 600:
                color = 'feffcd'
            elif taxa_count > 600 and taxa_count <= 725:
                color = 'dcf6c0'
            elif taxa_count > 725 and taxa_count <= 850:
                color = '8bdaba'
            elif taxa_count > 850 and taxa_count <= 975:
                color = '47c5c0'
            elif taxa_count > 975 and taxa_count <= 1100:
                color = '03aec3'
            elif taxa_count > 1100 and taxa_count <= 1225:
                color = '216db0'
            elif taxa_count > 1225 and taxa_count <= 1350:
                color = '2c3095'
        elif self.map_type == 'nonnative':
            if taxa_count > 120 and taxa_count <= 230:
                color = 'feffcd'
            elif taxa_count > 230 and taxa_count <= 340:
                color = 'dcf6c0'
            elif taxa_count > 340 and taxa_count <= 450:
                color = '8bdaba'
            elif taxa_count > 450 and taxa_count <= 560:
                color = '47c5c0'
            elif taxa_count > 560 and taxa_count <= 670:
                color = '03aec3'
            elif taxa_count > 670 and taxa_count <= 780:
                color = '216db0'
            elif taxa_count > 780 and taxa_count <= 890:
                color = '2c3095'
        elif self.map_type == 'all':
            if taxa_count > 640 and taxa_count <= 860:
                color = 'feffcd'
            elif taxa_count > 860 and taxa_count <= 1080:
                color = 'dcf6c0'
            elif taxa_count > 1080 and taxa_count <= 1300:
                color = '8bdaba'
            elif taxa_count > 1300 and taxa_count <= 1520:
                color = '47c5c0'
            elif taxa_count > 1520 and taxa_count <= 1740:
                color = '03aec3'
            elif taxa_count > 1740 and taxa_count <= 1960:
                color = '216db0'
            elif taxa_count > 1960 and taxa_count <= 2180:
                color = '2c3095'
        color = '#%s' % color
        return color

    def _shade_county(self, county, state, taxa_count):
        color = self._get_color(taxa_count)
        path_nodes = self.svg_map.xpath(self.PATH_NODES_XPATH,
            namespaces=NAMESPACES)
        state_and_county = '%s_%s' % (state.lower(),
            county.replace(' ', '_').lower())
        # When shading a map area, iterate over the nodes rather
        # than selecting a node via XPath. Iterating is around twice
        # as fast as XPath, at least when breaking after finding a node
        # as is done for the county-level records.
        for node in path_nodes:
            node_id = node.get('id').lower()
            if node_id == state_and_county:
                box = Path(node)
                box.color(color)

    def _fill_legend(self):
        border_color = '#000'
        if self.map_type == 'native':
            self.legend._set_item(1, '#feffcd', border_color, '475–600')
            self.legend._set_item(2, '#dcf6c0', border_color, '601–725')
            self.legend._set_item(3, '#8bdaba', border_color, '726–850')
            self.legend._set_item(4, '#47c5c0', border_color, '851–975')
            self.legend._set_item(5, '#03aec3', border_color, '976–1100')
            self.legend._set_item(6, '#216db0', border_color, '1101–1225')
            self.legend._set_item(7, '#2c3095', border_color, '1226–1350')
        elif self.map_type == 'nonnative':
            self.legend._set_item(1, '#feffcd', border_color, '120–230')
            self.legend._set_item(2, '#dcf6c0', border_color, '231–340')
            self.legend._set_item(3, '#8bdaba', border_color, '341–450')
            self.legend._set_item(4, '#47c5c0', border_color, '451–560')
            self.legend._set_item(5, '#03aec3', border_color, '561–670')
            self.legend._set_item(6, '#216db0', border_color, '671–780')
            self.legend._set_item(7, '#2c3095', border_color, '781–890')
        elif self.map_type == 'all':
            self.legend._set_item(1, '#feffcd', border_color, '640–860')
            self.legend._set_item(2, '#dcf6c0', border_color, '861–1080')
            self.legend._set_item(3, '#8bdaba', border_color, '1081–1300')
            self.legend._set_item(4, '#47c5c0', border_color, '1301–1520')
            self.legend._set_item(5, '#03aec3', border_color, '1521–1740')
            self.legend._set_item(6, '#216db0', border_color, '1741–1960')
            self.legend._set_item(7, '#2c3095', border_color, '1961–2180')

    def shade(self):
        """Shade a New England plant diversity map. Assumes the method
        set_data(data) has already been called.
        """
        for record in self.data:
            state, county, taxa_count = record
            if county != '(all counties)':
                self._shade_county(county, state, int(taxa_count))
        self._fill_legend()
        return self


class NewEnglandPlantDistributionMap(PlantDistributionMap):
    """Class for a map that shows New England county-level distribution
    data for a plant.
    """

    def __init__(self):
        # Note that this version of the New England counties map is
        # under the static directory. It is not to be confused with
        # versions in the "mapping" app's directory, which are used by
        # code that scans existing maps.
        blank_map_path  = GRAPHICS_ROOT + '/new-england-counties-scoured.svg'
        super(NewEnglandPlantDistributionMap, self).__init__(blank_map_path)


class NewEnglandPlantDiversityMap(PlantDiversityMap):
    """Class for a map that shows New England county-level plant diversity data.
    """

    def __init__(self):
        blank_map_path  = GRAPHICS_ROOT + '/new-england-counties-diversity.svg'
        super(NewEnglandPlantDiversityMap, self).__init__(blank_map_path)


class UnitedStatesPlantDistributionMap(PlantDistributionMap):
    """Class for a map that shows United States county-level distribution
    data for a plant.
    """

    PATH_NODES_XPATH = 'svg:g/svg:path'

    def __init__(self):
        blank_map_path  = GRAPHICS_ROOT + '/us-counties-scoured.svg'
        super(UnitedStatesPlantDistributionMap, self).__init__(blank_map_path)


class NorthAmericanPlantDistributionMap(PlantDistributionMap):
    """Class for a map that shows North American distribution data for a
    plant. Data for the United States are shown at the county level. Data
    for Canada are currently shown at the province level, not the county
    or county equivalent level, because it is not yet available. Also,
    only the southern parts of eight Canadian provinces are shown so far,
    because that is the extent of the available data.
    """

    PATH_NODES_XPATH = 'svg:g/svg:path'

    def __init__(self):
        blank_map_path = GRAPHICS_ROOT + '/north-america-scoured.svg'
        super(NorthAmericanPlantDistributionMap, self).__init__(
            blank_map_path)

    def _shade_areas(self):
        """Set the colors of the states, provinces, or territories.
        Originally we expected county-level data, at least for the U.S.,
        so this routine shades all county paths within a state.
        """
        legend_labels_found = []
        if self.distribution_records:
            path_nodes = self.svg_map.xpath(self.PATH_NODES_XPATH,
                namespaces=NAMESPACES)

            # Take a pass through the nodes and shade any
            # state-/province-/territory-level records.
            state_records = self.distribution_records.filter(county='')
            for record in state_records:
                for node in path_nodes:
                    id_province = node.get('id').split('_')[0].upper()
                    if id_province == record.state.upper():
                        label = self._get_label(record.present, record.native)
                        if label not in legend_labels_found:
                            legend_labels_found.append(label)
                        box = Path(node)
                        if self._should_shade(box, record.present,
                                record.native):
                            box.color(Legend.COLORS[label])
                        # Keep going rather than break, because
                        # there are often multiple paths to shade.

            # Take a pass through the nodes and override state shading 
            # if necessary based on county-level records.
            county_records = self.distribution_records.exclude(county='')
            for record in county_records:
                for node in path_nodes:
                    id_province = node.get('id').split('_')[0].upper()
                    if id_province == record.state.upper():
                        label = self._get_label(record.present, record.native)
                        if label not in legend_labels_found:
                            legend_labels_found.append(label)
                        box = Path(node)
                        if self._should_shade(box, record.present,
                                record.native):
                            box.color(Legend.COLORS[label])
                        break   # Move on to the next distribution record.

            legend_labels_found = self._order_labels(legend_labels_found)

            # Omit 'absent' from the items to display in the legend.
            if 'absent' in legend_labels_found:
                legend_labels_found.remove('absent')

        return legend_labels_found
