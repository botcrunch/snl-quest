from __future__ import absolute_import, print_function

import logging
from functools import partial
import webbrowser
import calendar
import os
import numpy as np
import threading

from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition, ScreenManagerException
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty, ListProperty, DictProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.animation import Animation
from kivy.clock import Clock, mainthread
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.modalview import ModalView
from kivy.uix.textinput import TextInput

# from es_gui.apps.valuation.reporting import Report
from .reporting import BtmCostSavingsReport
from es_gui.resources.widgets.common import BodyTextBase, MyPopup, WarningPopup, TileButton, RecycleViewRow, InputError, BASE_TRANSITION_DUR, BUTTON_FLASH_DUR, ANIM_STAGGER, FADEIN_DUR, SLIDER_DUR, PALETTE, rgba_to_fraction, fade_in_animation, WizardCompletePopup, ParameterRow


class CostSavingsWizard(Screen):
    """The main screen for the cost savings wizard. This hosts the nested screen manager for the actual wizard."""
    def on_enter(self):
        ab = self.manager.nav_bar
        ab.reset_nav_bar()
        ab.set_title('Time-of-Use Cost Savings')

        # self.sm.generate_start()

    def on_leave(self):
        # Reset wizard to initial state by removing all screens except the first.
        self.sm.current = 'start'

        if len(self.sm.screens) > 1:
            self.sm.clear_widgets(screens=self.sm.screens[1:])


class CostSavingsWizardScreenManager(ScreenManager):
    """The screen manager for the cost savings wizard screens."""
    def __init__(self, **kwargs):
        super(CostSavingsWizardScreenManager, self).__init__(**kwargs)

        self.transition = SlideTransition()
        self.add_widget(CostSavingsWizardStart(name='start'))
    
    # def generate_start(self):
    #     """"""
    #     try:
    #         data_manager = App.get_running_app().data_manager
    #         rate_structure_options = [rs[1] for rs in data_manager.get_rate_structures().items()]
    #         self.get_screen('start').rate_structure_rv.data = rate_structure_options
    #         self.get_screen('start').rate_structure_rv.unfiltered_data = rate_structure_options


class CostSavingsWizardStart(Screen):
    """The starting/welcome screen for the cost savings wizard."""
    def _next_screen(self):
        if not self.manager.has_screen('rate_select'):
            screen = CostSavingsWizardRateSelect(name='rate_select')
            self.manager.add_widget(screen)

        self.manager.transition.duration = BASE_TRANSITION_DUR
        self.manager.transition.direction = 'left'
        self.manager.current = 'rate_select'


class CostSavingsWizardRateSelect(Screen):
    """The starting/welcome screen for the cost savings wizard."""
    rate_structure_selected = DictProperty()
    has_selection = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(CostSavingsWizardRateSelect, self).__init__(**kwargs)

        CostSavingsRateStructureRVEntry.host_screen = self
    
    def on_enter(self):
        try:
            data_manager = App.get_running_app().data_manager
            rate_structure_options = [rs[1] for rs in data_manager.get_rate_structures().items()]
            self.rate_structure_rv.data = rate_structure_options
            self.rate_structure_rv.unfiltered_data = rate_structure_options
        except KeyError as e:
            logging.warning('CostSavings: No rate structures available to select.')
            # TODO: Warning popup
        
        Clock.schedule_once(partial(fade_in_animation, self.content), 0)
    
    def on_leave(self):
        Animation.stop_all(self.content, 'opacity')
        self.content.opacity = 0
    
    def on_rate_structure_selected(self, instance, value):
        try:
            logging.info('CostSavings: Rate structure selection changed to {0}.'.format(value['name']))
        except KeyError:
            logging.info('CostSavings: Rate structure selection reset.')
            self.rate_structure_desc.text = ''
            self.has_selection = False
        else:
            Animation.stop_all(self.preview_box, 'opacity')
            self.preview_box.opacity = 0

            def _generate_preview():
                self.generate_schedule_charts()
                self.generate_flat_demand_rate_table()
                self.generate_misc_table()

                Clock.schedule_once(partial(fade_in_animation, self.preview_box), 0)
                self.has_selection = True
            
            thread_preview = threading.Thread(target=_generate_preview)
            thread_preview.start()

    def on_has_selection(self, instance, value):
        self.next_button.disabled = not value            

    def generate_flat_demand_rate_table(self):
        """Generates the preview table for the flat demand rate structure."""
        flat_demand_rates = self.rate_structure_selected['demand rate structure'].get('flat rates', {})

        table_data = [str(flat_demand_rates.get(month, '')) for month in calendar.month_abbr[1:]]
        self.flat_demand_rates_table.populate_table(table_data)
        
    def generate_misc_table(self):
        """Generates the preview table for the miscellaneous information."""
        self.misc_data_table.populate_table(self.rate_structure_selected)

    def generate_schedule_charts(self, *args):
        """Generates the preview for the weekday and weekend rate schedule charts."""
        weekday_schedule_data = self.rate_structure_selected['energy rate structure'].get('weekday schedule', [])
        weekend_schedule_data = self.rate_structure_selected['energy rate structure'].get('weekend schedule', [])

        legend_labels = ['${0}/kWh'.format(v) for _,v in self.rate_structure_selected['energy rate structure'].get('energy rates').items()]

        if weekday_schedule_data and weekend_schedule_data:
            n_tiers = len(np.unique(weekday_schedule_data))

            palette = [rgba_to_fraction(color) for color in PALETTE][:n_tiers]
            labels = calendar.month_abbr[1:]

            self.energy_weekday_chart.draw_chart(np.array(weekday_schedule_data), palette, labels, legend_labels=legend_labels)
            self.energy_weekend_chart.draw_chart(np.array(weekend_schedule_data), palette, labels, legend_labels=legend_labels)
        
        weekday_schedule_data = self.rate_structure_selected['demand rate structure'].get('weekday schedule', [])
        weekend_schedule_data = self.rate_structure_selected['demand rate structure'].get('weekend schedule', [])

        legend_labels = ['${0}/kW'.format(v) for _,v in self.rate_structure_selected['demand rate structure'].get('time of use rates').items()]

        if weekday_schedule_data and weekend_schedule_data:
            n_tiers = len(np.unique(weekday_schedule_data))

            # Select chart colors.
            palette = [rgba_to_fraction(color) for color in PALETTE][:n_tiers]
            labels = calendar.month_abbr[1:]

            # Draw charts.
            self.demand_weekday_chart.draw_chart(np.array(weekday_schedule_data), palette, labels, legend_labels=legend_labels)
            self.demand_weekend_chart.draw_chart(np.array(weekend_schedule_data), palette, labels, legend_labels=legend_labels)
    
    def _validate_inputs(self):
        # TODO: Progress already impeded until a structure is selected so...
        return self.rate_structure_selected
    
    def get_selections(self):
        """Retrieves screen's selections."""
        try:
            rate_structure_selected = self._validate_inputs()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            return rate_structure_selected

    def _next_screen(self):
        if not self.manager.has_screen('load_profile_select'):
            screen = CostSavingsWizardLoadSelect(name='load_profile_select')
            self.manager.add_widget(screen)
        
        try:
            self.get_selections()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            self.manager.transition.duration = BASE_TRANSITION_DUR
            self.manager.transition.direction = 'left'
            self.manager.current = 'load_profile_select'


class CostSavingsRateStructureRVEntry(RecycleViewRow):
    host_screen = None

    def apply_selection(self, rv, index, is_selected):
        """Respond to the selection of items in the view."""
        super(CostSavingsRateStructureRVEntry, self).apply_selection(rv, index, is_selected)

        if is_selected:
            self.host_screen.rate_structure_selected = rv.data[self.index]


class FlatDemandRateTable(GridLayout):
    """A preview table to show the monthly flat demand rate structure."""
    def reset_table(self):
        """Builds the table column headers if necessary and removes all data entries."""
        if not self.col_headers.children:
            for month in calendar.month_abbr[1:]:
                col_header = BodyTextBase(text=month, color=rgba_to_fraction(PALETTE[1]), font_size=20)
                self.col_headers.add_widget(col_header)
        
        while len(self.data_grid.children) > 0:
            for widget in self.data_grid.children:
                self.data_grid.remove_widget(widget)
    
    def populate_table(self, data):
        """Populates the data entries."""
        self.reset_table()

        for datum in data:
            rate_label = BodyTextBase(text=datum, font_size=20)
            self.data_grid.add_widget(rate_label)


class MiscRateStructureDataTable(GridLayout):
    """A preview table for miscellaneous rate structure information."""
    def reset_table(self):
        """Removes all data entries."""
        while len(self.peak_min_box.children) > 0:
            for widget in self.peak_min_box.children:
                self.peak_min_box.remove_widget(widget)

        while len(self.peak_max_box.children) > 0:
            for widget in self.peak_max_box.children:
                self.peak_max_box.remove_widget(widget)
                
        while len(self.net_metering_type_box.children) > 0:
            for widget in self.net_metering_type_box.children:
                self.net_metering_type_box.remove_widget(widget)
        
        while len(self.energy_sell_price_box.children) > 0:
            for widget in self.energy_sell_price_box.children:
                self.energy_sell_price_box.remove_widget(widget)
    
    def populate_table(self, rate_structure_dict):
        """Populates the table with data from the rate structure dictionary."""
        self.reset_table()

        net_metering_dict = rate_structure_dict['net metering']
        demand_structure_dict = rate_structure_dict['demand rate structure']

        peak_kw_min = str(demand_structure_dict.get('minimum peak demand', '0'))
        peak_kw_min_label = TextInput(text=peak_kw_min, font_size=20, readonly=True)
        self.peak_min_box.add_widget(peak_kw_min_label)

        peak_kw_max = str(demand_structure_dict.get('maximum peak demand', 'None'))
        peak_kw_max_label = TextInput(text=peak_kw_max, font_size=20, readonly=True)
        self.peak_max_box.add_widget(peak_kw_max_label)

        net_metering_type = '2.0' if net_metering_dict['type'] else '1.0'
        net_metering_type_label = TextInput(text=net_metering_type, font_size=20, readonly=True)
        self.net_metering_type_box.add_widget(net_metering_type_label)

        energy_sell_price = 'N/A' if not net_metering_dict.get('energy sell price', False) else str(net_metering_dict.get('energy sell price', ''))
        energy_sell_price_label = TextInput(text=energy_sell_price, font_size=20, readonly=True)
        self.energy_sell_price_box.add_widget(energy_sell_price_label)
        

class CostSavingsWizardLoadSelect(Screen):
    """The load profile selection screen for the cost savings wizard."""
    load_profile_selected = DictProperty()
    has_selection = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(CostSavingsWizardLoadSelect, self).__init__(**kwargs)

        LoadProfileRecycleViewRow.load_profile_screen = self

    def on_enter(self):
        try:
            data_manager = App.get_running_app().data_manager

            load_profile_options = [{'name': x[0], 'path': x[1]} for x in data_manager.get_load_profiles().items()]
            self.load_profile_rv.data = load_profile_options
            self.load_profile_rv.unfiltered_data = load_profile_options
        except KeyError as e:
            logging.warning('CostSavings: No load profiles available to select.')
            # TODO: Warning popup
        
        Clock.schedule_once(partial(fade_in_animation, self.content), 0)
    
    def on_leave(self):
        Animation.stop_all(self.content, 'opacity')
        self.content.opacity = 0
    
    def on_load_profile_selected(self, instance, value):
        try:
            logging.info('CostSavings: Load profile selection changed to {0}.'.format(value['name']))
        except KeyError:
            logging.info('CostSavings: Load profile selection reset.')
            self.has_selection = False
        else:
            self.has_selection = True

    def on_has_selection(self, instance, value):
        self.next_button.disabled = not value
    
    def _validate_inputs(self):
        # TODO: Progress already impeded until a profile is selected so...
        return self.load_profile_selected
    
    def get_selections(self):
        """Retrieves screen's selections."""
        try:
            load_profile_selected = self._validate_inputs()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            return load_profile_selected
    
    def _next_screen(self):
        if not self.manager.has_screen('pv_profile_select'):
            screen = CostSavingsWizardPVSelect(name='pv_profile_select')
            self.manager.add_widget(screen)
        
        try:
            self.get_selections()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            self.manager.transition.duration = BASE_TRANSITION_DUR
            self.manager.transition.direction = 'left'
            self.manager.current = 'pv_profile_select'


class LoadProfileRecycleViewRow(RecycleViewRow):
    """The representation widget for node in the load profile selector RecycleView."""
    load_profile_screen = None

    def on_touch_down(self, touch):
        """Add selection on touch down."""
        if super(LoadProfileRecycleViewRow, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        """Respond to the selection of items in the view."""
        self.selected = is_selected

        if is_selected:
            self.load_profile_screen.load_profile_selected = rv.data[self.index]


class CostSavingsWizardPVSelect(Screen):
    """The optional PV profile selection screen for the cost savings wizard."""
    pv_profile_selected = DictProperty()

    def __init__(self, **kwargs):
        super(CostSavingsWizardPVSelect, self).__init__(**kwargs)

        PVProfileRecycleViewRow.pv_profile_screen = self

    def on_enter(self):
        try:
            data_manager = App.get_running_app().data_manager

            load_profile_options = [{'name': x[0], 'path': x[1]} for x in data_manager.get_pv_profiles().items()]
            self.pv_profile_rv.data = load_profile_options
            self.pv_profile_rv.unfiltered_data = load_profile_options
        except Exception as e:
            print(e)
        
        Clock.schedule_once(partial(fade_in_animation, self.content), 0)
        
    def on_leave(self):
        Animation.stop_all(self.content, 'opacity')
        self.content.opacity = 0
    
    def on_load_profile_selected(self, instance, value):
        try:
            logging.info('CostSavings: Load profile selection changed to {0}.'.format(value['name']))
        except KeyError:
            logging.info('CostSavings: Load profile selection reset.')
            self.has_selection = False
        else:
            self.has_selection = True
    
    def _validate_inputs(self):
        return self.pv_profile_selected
    
    def get_selections(self):
        """Retrieves screen's selections."""
        try:
            pv_profile_selected = self._validate_inputs()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            return pv_profile_selected
    
    def _next_screen(self):
        if not self.manager.has_screen('system_parameters'):
            screen = CostSavingsWizardSystemParameters(name='system_parameters')
            self.manager.add_widget(screen)

        self.manager.transition.duration = BASE_TRANSITION_DUR
        self.manager.transition.direction = 'left'
        self.manager.current = 'system_parameters'


class PVProfileRecycleViewRow(RecycleViewRow):
    """The representation widget for node in the PV profile selector RecycleView."""
    pv_profile_screen = None

    def on_touch_down(self, touch):
        """Add selection on touch down."""
        if super(PVProfileRecycleViewRow, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        """Respond to the selection of items in the view."""
        self.selected = is_selected

        if is_selected:
            self.pv_profile_screen.load_profile = rv.data[self.index]


class CostSavingsWizardSystemParameters(Screen):
    """"""
    def on_pre_enter(self):
        if not self.param_widget.children:
            self.param_widget.build()
        # while len(self.param_widget.children) > 0:
        #     for widget in self.param_widget.children:
        #         if isinstance(widget, CostSavingsParameterRow):
        #             self.param_widget.remove_widget(widget)
    
    def on_enter(self):
        Clock.schedule_once(partial(fade_in_animation, self.content), 0)
    
    def on_leave(self):
        Animation.stop_all(self.content, 'opacity')
        self.content.opacity = 0
    
    def _validate_inputs(self):
        params = self.param_widget.get_inputs()

        return params
    
    def get_selections(self):
        """Retrieves screen's selections."""
        try:
            params = self._validate_inputs()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            return params
    
    def _next_screen(self):
        if not self.manager.has_screen('summary'):
            screen = CostSavingsWizardSummary(name='summary')
            self.manager.add_widget(screen)
        
        try:
            self.get_selections()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            self.manager.transition.duration = BASE_TRANSITION_DUR
            self.manager.transition.direction = 'left'
            self.manager.current = 'summary'


class CostSavingsParameterWidget(GridLayout):
    """Grid layout containing rows of parameter adjustment widgets."""
    def build(self):
        # Build the widget by creating a row for each parameter.
        data_manager = App.get_running_app().data_manager
        MODEL_PARAMS = data_manager.get_btm_cost_savings_model_params()

        for param in MODEL_PARAMS:
            row = ParameterRow(desc=param)
            self.add_widget(row)
            setattr(self, param['attr name'], row)
    
    def _validate_inputs(self):
        params = []
        param_set = {}

        for row in self.children:
            attr_name = row.desc['attr name']

            if not row.text_input.text:
                attr_val = row.text_input.hint_text
            else:
                attr_val = row.text_input.text
            
            param_set[attr_name] = float(attr_val)
        
        params.append(param_set)

        return params
    
    def get_inputs(self):
        try:
            params = self._validate_inputs()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            return params


# class CostSavingsParameterRow(GridLayout):
#     """Grid layout containing parameter name, description, text input, and units."""
#     def __init__(self, desc, **kwargs):
#         super(CostSavingsParameterRow, self).__init__(**kwargs)

#         self._desc = desc

#         self.name.text = self.desc.get('name', '')
#         self.notes.text = self.desc.get('notes', '')
#         self.text_input.hint_text = str(self.desc.get('default', ''))
#         self.units.text = self.desc.get('units', '')

#     @property
#     def desc(self):
#         return self._desc

#     @desc.setter
#     def desc(self, value):
#         self._desc = value


# class CostSavingsParamTextInput(TextInput):
#     """
#     A TextInput field for entering parameter values. Limited to float values.
#     """
#     def insert_text(self, substring, from_undo=False):
#         # limit to 8 chars
#         substring = substring[:8 - len(self.text)]
#         return super(CostSavingsParamTextInput, self).insert_text(substring, from_undo=from_undo)


class CostSavingsWizardSummary(Screen):
    """"""
    def get_selections(self):
        sm = self.manager

        op_handler_requests = {}

        op_handler_requests['rate_structure'] = sm.get_screen('rate_select').get_selections()
        op_handler_requests['load_profile'] = sm.get_screen('load_profile_select').get_selections()
        op_handler_requests['pv_profile'] = sm.get_screen('pv_profile_select').get_selections()
        op_handler_requests['params'] = sm.get_screen('system_parameters').get_selections()

        return op_handler_requests

    def on_enter(self):
        Clock.schedule_once(partial(fade_in_animation, self.content), 0)

        op_handler_requests = self.get_selections()

        print(op_handler_requests)
    
    def on_leave(self):
        Animation.stop_all(self.content, 'opacity')
        self.content.opacity = 0

    def _next_screen(self):
        if not self.manager.has_screen('execute'):
            screen = CostSavingsWizardExecute(name='execute')
            self.manager.add_widget(screen)
        
        self.manager.transition.duration = BASE_TRANSITION_DUR
        self.manager.transition.direction = 'left'
        self.manager.current = 'execute'


class CostSavingsWizardExecute(Screen):
    """The screen for executing the prescribed optimizations for the cost savings wizard."""
    solved_ops = []
    report_attributes = {}

    def on_enter(self):
        self.execute_run()

    # def on_leave(self):
    #     self.progress_label.text = 'This may take a while. Please wait patiently!'

    def execute_run(self):
        btm_home = self.manager.parent.parent.manager.get_screen('btm_home')
        ss = self.manager.get_screen('summary')

        op_handler_requests = ss.get_selections()

        # Send requests to handler.
        handler = btm_home.handler
        handler.solver_name = App.get_running_app().config.get('optimization', 'solver')
        self.solved_ops, handler_status = handler.process_requests(op_handler_requests)

        # If no optimizations were solved successfully, bail out.
        if not self.solved_ops:
            popup = CostSavingsWizardCompletePopup()

            popup.title = "Hmm..."
            popup.popup_text.text = "Unfortunately, none of the models were able to be solved."
            popup.results_button.text = "Take me back"
            popup.bind(on_dismiss=lambda x: self.manager.parent.parent.manager.nav_bar.go_up_screen())  # Go back to BTM Home
            popup.open()
            return
        
        self.report_attributes = []

        # # Save selection summary details to pass to report generator.
        # deviceSelectionButtons = self.manager.get_screen('device_select').device_select.children
        # selectedDeviceName = [x.text for x in deviceSelectionButtons if x.state == "down"][0]

        # self.report_attributes = {'market area': iso,
        #                           'pricing node': node,
        #                           'selected device': selectedDeviceName,
        #                           'dates analyzed': ' to '.join([
        #                               ' '.join([calendar.month_name[int(hist_data[0]['month'])], hist_data[0]['year']]),
        #                               ' '.join([calendar.month_name[int(hist_data[-1]['month'])], hist_data[-1]['year']]),
        #                               ]),
        #                           'revenue streams': wiz_selections['rev_streams'],
        #                           'market type': rev_streams,
        #                          }

        # for param in device:
        #     self.report_attributes[param.desc['attr name']] = param.param_slider.value

        popup = WizardCompletePopup()

        if not handler_status:
            popup.title = "Success!*"
            popup.popup_text.text = "All calculations finished. Press 'OK' to proceed to the results.\n\n*At least one model (month) had issues being built and/or solved. Any such model will be omitted from the results."

        popup.bind(on_dismiss=self._next_screen)
        popup.open()

    def _next_screen(self, *args):
        """Adds the report screen if it does not exist and changes screens to it."""
        report = BtmCostSavingsReport(name='report', chart_data=self.solved_ops, report_attributes=self.report_attributes)
        self.manager.switch_to(report, direction='left', duration=BASE_TRANSITION_DUR)
        # pass
