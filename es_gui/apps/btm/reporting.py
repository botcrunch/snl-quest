from random import sample, choice
from functools import partial
from collections import OrderedDict
import calendar
import os
import datetime
import webbrowser
import base64
from time import sleep

from jinja2 import Environment, FileSystemLoader, select_autoescape
from kivy.uix.screenmanager import Screen, ScreenManager, WipeTransition, NoTransition
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.modalview import ModalView
from kivy.clock import Clock

from es_gui.tools.charts import BarChart, StackedBarChart, MultisetBarChart, PieChart, DonutChart, format_dollar_string
from es_gui.resources.widgets.common import TWO_ABC_WIDTH, THREE_ABC_WIDTH, MyPopup, TileButton, PALETTE, rgba_to_fraction, ReportScreen, WizardReportInterface, ReportChartToggle


class BtmCostSavingsReport(WizardReportInterface):
    chart_types = OrderedDict({
        'Total bill (by month)': 'total_bill_bar',
        # 'Total bill (by source)': 'total_bill_stacked',
        'Total bill comparison': 'total_bill_comparison_multiset',
        'Demand charge comparison': 'demand_charge_comparison_multiset',
        'Energy charge comparison': 'energy_charge_comparison_multiset',
        'NEM comparison': 'nem_comparison_multiset',
        # 'Total savings': 'total_savings_donut',
                   })
    
    # Sometimes the charges/bills/savings can be negative so we can't use stacked bar or donut charts.

    def __init__(self, chart_data, report_attributes, **kwargs):
        super(BtmCostSavingsReport, self).__init__(**kwargs)

        self.chart_type = type
        self.chart_data = chart_data
        self.report_attributes = report_attributes

        sm = self.report_sm

        # Build chart type selection buttons and corresponding report screens.
        for opt in self.chart_types.items():
            button = ReportChartToggle(text=opt[0])
            button.bind(state=partial(self.add_report, opt[1]))
            self.chart_type_toggle.add_widget(button)

            screen = BtmCostSavingsReportScreen(type=opt[1], chart_data=self.chart_data, name=opt[1])
            sm.add_widget(screen)

    def add_report(self, chart_type, *args):
        # Adds a ReportScreen of type chart_type to the screen manager.
        sm = self.report_sm
        sm.transition = WipeTransition(duration=0.8, clearcolor=[1, 1, 1, 1])

        if not sm.has_screen(chart_type):
            screen = BtmCostSavingsReportScreen(type=chart_type, chart_data=self.chart_data, name=chart_type)
            sm.add_widget(screen)

        sm.current = chart_type
    
    def open_generate_report_menu(self):
        GenerateReportMenu.host_report = self
        gen_report_menu = GenerateReportMenu()
        gen_report_menu.open()


class ReportScreenManager(ScreenManager):
    transition = WipeTransition(duration=0.8, clearcolor=[1, 1, 1, 1])


class BtmCostSavingsReportScreen(ReportScreen):
    """A report screen for the BTM Cost Savings Wizard."""

    def __init__(self, type, chart_data, do_animation=True, **kwargs):
        super(BtmCostSavingsReportScreen, self).__init__(**kwargs)

        self.chart_type = type
        self.chart_data = chart_data
        self.do_animation = do_animation

        if self.chart_type == 'total_bill_bar':
            self.chart_bx.orientation = 'vertical'

            #self.desc.width = THREE_ABC_WIDTH
            self.desc_bx.size_hint_y = 0.33

            self.chart = BarChart(bar_spacing=25, y_axis_format='${0:,.0f}', size_hint_x=1.0, do_animation=self.do_animation)
            self.bind(on_enter=self.generate_total_bill_bar_chart)
        elif self.chart_type == 'total_bill_comparison_multiset':
            self.chart_bx.orientation = 'vertical'

            #self.desc.width = THREE_ABC_WIDTH
            self.desc_bx.size_hint_y = 0.33

            self.chart = MultisetBarChart(bar_spacing=25, legend_width=TWO_ABC_WIDTH/4, y_axis_format='${0:,.0f}', size_hint_x=1.0, do_animation=self.do_animation)
            self.bind(on_enter=self.generate_total_bill_comparison_chart)
        elif self.chart_type == 'demand_charge_comparison_multiset':
            self.chart_bx.orientation = 'vertical'

            #self.desc.width = THREE_ABC_WIDTH
            self.desc_bx.size_hint_y = 0.33

            self.chart = MultisetBarChart(bar_spacing=25, legend_width=TWO_ABC_WIDTH/4, y_axis_format='${0:,.0f}', size_hint_x=1.0, do_animation=self.do_animation)
            self.bind(on_enter=self.generate_demand_charge_comparison_chart)
        elif self.chart_type == 'energy_charge_comparison_multiset':
            self.chart_bx.orientation = 'vertical'

            #self.desc.width = THREE_ABC_WIDTH
            self.desc_bx.size_hint_y = 0.33

            self.chart = MultisetBarChart(bar_spacing=25, legend_width=TWO_ABC_WIDTH/4, y_axis_format='${0:,.0f}', size_hint_x=1.0, do_animation=self.do_animation)
            self.bind(on_enter=self.generate_energy_charge_comparison_chart)
        elif self.chart_type == 'nem_comparison_multiset':
            self.chart_bx.orientation = 'vertical'

            #self.desc.width = THREE_ABC_WIDTH
            self.desc_bx.size_hint_y = 0.33

            self.chart = MultisetBarChart(bar_spacing=25, legend_width=TWO_ABC_WIDTH/4, y_axis_format='${0:,.0f}', size_hint_x=1.0, do_animation=self.do_animation)
            self.bind(on_enter=self.generate_nem_charge_comparison_chart)
        elif self.chart_type == 'total_savings_donut':
            self.chart_bx.orientation = 'vertical'

            #self.desc.width = THREE_ABC_WIDTH
            self.desc_bx.size_hint_y = 0.66

            self.chart = DonutChart(do_animation=self.do_animation)
            self.bind(on_enter=self.generate_total_savings_donut_chart)
        elif self.chart_type == 'total_bill_stacked':
            self.chart_bx.orientation = 'vertical'

            #self.desc.width = THREE_ABC_WIDTH
            self.desc_bx.size_hint_y = 0.33

            self.chart = StackedBarChart(bar_spacing=25, legend_width=TWO_ABC_WIDTH/4, y_axis_format='${0:,.0f}', size_hint_x=1.0, do_animation=self.do_animation)
            self.bind(on_enter=self.generate_total_bill_stackedbar_chart)
        else:
            raise(ValueError('An improper chart type was specified. (got {0})'.format(self.chart_type)))

        self.chart_bx.add_widget(self.chart)

    def on_leave(self):
        # reset the chart
        self.chart.clear_widgets()

    def generate_total_bill_bar_chart(self, *args):
        """Generates bar chart showing the total bill with energy storage each month."""
        bar_data = []

        if len(self.chart_data) > len(PALETTE):
            colors = PALETTE
        else:
            colors = sample(PALETTE, len(self.chart_data))

        for ix, op in enumerate(self.chart_data, start=0):
            name = op[0]
            _, month, _ = name.split(' | ')
            label = month

            solved_op = op[1]
            results = solved_op.results

            bar_color = colors[divmod(ix, len(colors))[1]]
            bar_data.append([label, rgba_to_fraction(bar_color), float(solved_op.total_bill_with_es)])

        self.chart.draw_chart(bar_data)
        max_bar = self.chart.max_bar
        min_bar = self.chart.min_bar

        # generate report text
        self.title.text = "Here's the total bill for each month."
        self.desc.text = 'The total bill is the sum of demand charges, energy charges, and net metering charges. '

        total_charges_str = format_dollar_string(sum(op[1].total_bill_with_es for op in self.chart_data))
        month_high_str = format_dollar_string(max_bar.value)
        month_low_str = format_dollar_string(min_bar.value)

        report_templates = [
        'The total charges for the year was [b]{0}[/b].'.format(total_charges_str),
        'The highest bill for a month was [b]{0}[/b] in [b]{1}[/b].'.format(month_high_str, calendar.month_name[list(calendar.month_abbr).index(max_bar.name)]),
        'The lowest bill for a month was [b]{0}[/b] in [b]{1}[/b].'.format(month_low_str, calendar.month_name[list(calendar.month_abbr).index(min_bar.name)]),
        ]

        self.desc.text += ' '.join(report_templates)

    def generate_total_bill_comparison_chart(self, *args):
        """Generates the multiset bar chart comparing total bill with and without energy storage each month."""
        n_cats = 2

        if n_cats > len(PALETTE):
            colors = PALETTE
        else:
            colors = sample(PALETTE, n_cats)

        multisetbar_data = OrderedDict()

        for ix, op in enumerate(self.chart_data, start=0):
            name = op[0]
            _, month, _ = name.split(' | ')
            label = month

            solved_op = op[1]

            bar_group = [['without ES', rgba_to_fraction(colors[0]), float(solved_op.total_bill_without_es)]]
            bar_group.append(['with ES', rgba_to_fraction(colors[1]), float(solved_op.total_bill_with_es)])

            multisetbar_data[label] = bar_group

        self.chart.draw_chart(multisetbar_data)

        # generate report text
        self.title.text = "Here's the total bill with and without energy storage for each month."
        self.desc.text = 'The total bill is the sum of demand charges, energy charges, and net metering charges or credits. '

        report_templates = [
        ]

        self.desc.text += ' '.join(report_templates)
    
    def generate_demand_charge_comparison_chart(self, *args):
        """Generates the multiset bar chart comparing total demand charges with and without energy storage each month."""
        if any(op[1].has_demand_charges() for op in self.chart_data):
            n_cats = 2

            if n_cats > len(PALETTE):
                colors = PALETTE
            else:
                colors = sample(PALETTE, n_cats)

            multisetbar_data = OrderedDict()

            for ix, op in enumerate(self.chart_data, start=0):
                name = op[0]
                _, month, _ = name.split(' | ')
                label = month

                solved_op = op[1]
                results = solved_op.results

                bar_group = [['without ES', rgba_to_fraction(colors[0]), float(solved_op.demand_charge_without_es)]]
                bar_group.append(['with ES', rgba_to_fraction(colors[1]), float(solved_op.demand_charge_with_es)])

                multisetbar_data[label] = bar_group

            self.chart.draw_chart(multisetbar_data)

            self.title.text = "Here are the demand charge totals each month."
            self.desc.text = 'The demand charge etc. etc. '
            report_templates = [
            ]

            self.desc.text += ' '.join(report_templates)
        else:
            self.title.text = "It looks like there were no demand charges."
            self.desc.text = "The particular rate structure you selected resulted in no demand charges. Either there are no demand charges or no savings on demand charges were accrued using energy storage."

    
    def generate_energy_charge_comparison_chart(self, *args):
        """Generates the multiset bar chart comparing total energy charges with and without energy storage each month."""
        if any(op[1].has_energy_charges() for op in self.chart_data):
            n_cats = 2

            if n_cats > len(PALETTE):
                colors = PALETTE
            else:
                colors = sample(PALETTE, n_cats)

            multisetbar_data = OrderedDict()

            for ix, op in enumerate(self.chart_data, start=0):
                name = op[0]
                _, month, _ = name.split(' | ')
                label = month

                solved_op = op[1]
                results = solved_op.results

                bar_group = [['without ES', rgba_to_fraction(colors[0]), float(solved_op.energy_charge_without_es)]]
                bar_group.append(['with ES', rgba_to_fraction(colors[1]), float(solved_op.energy_charge_with_es)])

                multisetbar_data[label] = bar_group

            self.chart.draw_chart(multisetbar_data)

            self.title.text = "Here are the energy charge totals each month."
            self.desc.text = 'The energy charge etc. etc. '
            report_templates = [
            ]

            self.desc.text += ' '.join(report_templates)
        else:
            self.title.text = "It looks like there were no energy charges."
            self.desc.text = "The particular rate structure you selected resulted in no energy charges. Either there are no time-of-use energy charges or no savings on energy charges were accrued using energy storage."
    
    def generate_nem_charge_comparison_chart(self, *args):
        """Generates the multiset bar chart comparing total net energy metering charges with and without energy storage each month."""
        if any(op[1].has_nem_charges() for op in self.chart_data):
            n_cats = 2

            if n_cats > len(PALETTE):
                colors = PALETTE
            else:
                colors = sample(PALETTE, n_cats)

            multisetbar_data = OrderedDict()

            for ix, op in enumerate(self.chart_data, start=0):
                name = op[0]
                _, month, _ = name.split(' | ')
                label = month

                solved_op = op[1]

                bar_group = [['without ES', rgba_to_fraction(colors[0]), float(solved_op.nem_charge_without_es)]]
                bar_group.append(['with ES', rgba_to_fraction(colors[1]), float(solved_op.nem_charge_with_es)])

                multisetbar_data[label] = bar_group
            
            self.chart.draw_chart(multisetbar_data)

            self.title.text = "Here are the net energy metering (NEM) totals each month."

            net_metering_type = self.chart_data[0][1].nem_type
            net_metering_rate = self.chart_data[0][1].nem_rate
            
            if net_metering_type == 2:
                net_metering_type_str = '[b]Net energy metering 2.0[/b] uses the time-of-use energy rate for energy.'
            else:
                net_metering_type_str = '[b]Net energy metering 1.0[/b] uses a fixed price for energy, which was [b]{0}[/b]/kWh.'.format(format_dollar_string(net_metering_rate))

            self.desc.text = "{0} Negative values represent credits. ".format(net_metering_type_str)
            report_templates = [
            ]

            total_nem_difference = sum(op[1].nem_charge_with_es - op[1].nem_charge_without_es for op in self.chart_data)

            relation = 'increase' if total_nem_difference < 0 else 'decrease'
            total_difference_str = "The total [b]{0}[/b] in NEM credits with energy storage was [b]{1}[/b].".format(relation, format_dollar_string(abs(total_nem_difference)))
            report_templates.append(total_difference_str)

            self.desc.text += ' '.join(report_templates)
        else:
            self.title.text = "It looks like there were no net energy metering charges or credits."
            self.desc.text = "The particular rate structure you selected resulted in no net energy metering charges. Either that or no savings on net energy metering charges were accrued using energy storage."

    def generate_total_savings_donut_chart(self, *args):
        """TODO: Probably deprecate this since we can't guarantee non-negative quantities."""
        donut_data = []
        savings_sources = [
            ('energy charges', 'energy_charge_with_es', 'energy_charge_without_es'),
            ('demand charges', 'demand_charge_with_es', 'demand_charge_without_es'),
            ('NEM charges', 'nem_charge_with_es', 'nem_demand_charge_without_es'),
        ]
        total_savings = 0

        if sum([x[1].nem_charge_without_es for x in self.chart_data]) + sum([x[1].nem_charge_with_es for x in self.chart_data]) <= 0:
            n_cats = 2
        else:
            n_cats = 3

        if n_cats > len(PALETTE):
            colors = PALETTE
        else:
            colors = sample(PALETTE, n_cats)

        for ix, source in enumerate(savings_sources[:n_cats], start=0):
            savings = sum([getattr(op[1], source[-1]) - getattr(op[1], source[1]) for op in self.chart_data])
            total_savings += savings

            donut_data.append([source[0], rgba_to_fraction(colors[ix]), savings])

        # generate chart
        self.chart.draw_chart(donut_data)

        # generate report text
        self.title.text = "Here are the savings from each charge source when using energy storage."
        self.desc.text = ''
        report_templates = [
            'The [b]total[/b] savings from energy storage was [b]${0:,.2f}[/b].'.format(total_savings),
        ]

        self.desc.text += ' '.join(report_templates)

    def generate_total_bill_stackedbar_chart(self, *args):
        """TODO: Probably deprecate this since we can't guarantee non-negative quantities."""
        stackedbar_data = OrderedDict()

        charge_sources = [
            ('energy charges', 'energy_charge_with_es'),
            ('demand charges', 'demand_charge_with_es'),
            ('NEM charges', 'nem_charge_with_es'),
        ]

        if sum([x[1].nem_charge_without_es for x in self.chart_data]) + sum([x[1].nem_charge_with_es for x in self.chart_data]) == 0:
            n_cats = 2
        else:
            n_cats = 3

        if n_cats > len(PALETTE):
            colors = PALETTE
        else:
            colors = sample(PALETTE, n_cats)

        for op in self.chart_data:
            name = op[0]
            _, month, _ = name.split(' | ')
            label = month

            solved_op = op[1]
            bar_stack = []

            for iy, source in enumerate(charge_sources[:n_cats], start=0):
                component_color = colors[iy]
                savings = float(getattr(solved_op, source[-1]))

                bar_stack.append([source[0], rgba_to_fraction(component_color), savings])

            stackedbar_data[label] = bar_stack

        self.chart.draw_chart(stackedbar_data)

        self.title.text = "Here's the breakdown of the total bill with energy storage each month."
        self.desc.text = ''

        report_templates = [
        ]

        self.desc.text += ' '.join(report_templates)


class GenerateReportMenu(ModalView):
    host_report = None
    graphicsLocations = {}

    def __init__(self, **kwargs):
        super(GenerateReportMenu, self).__init__(**kwargs)

        self.sm.transition = NoTransition()

    def save_figure(self, screen, *args):
        if not self.sm.has_screen(screen.name):
            self.sm.add_widget(screen)

        self.sm.current = screen.name
        chart_dir = os.path.join('results', 'valuation', 'report', 'images')
        os.makedirs(chart_dir, exist_ok=True)

        chartSaveLocation = os.path.join(chart_dir, 'chart_{n}.png'.format(n=screen.name))

        Clock.schedule_once(partial(screen.chart.export_to_png, chartSaveLocation), 0.7)

        # Save image name/path for report generator.
        self.graphicsLocations[screen.name] = os.path.join('images', 'chart_{n}.png'.format(n=screen.name))

    def generate_report_screens(self):
        screenFlipInterval = 0.8
        nCharts = len(self.host_report.chart_types.items())

        # Draw figures for saving to .png.
        for ix, opt in enumerate(self.host_report.chart_types.items(), start=0):
            screen = ReportScreen(type=opt[1], chart_data=self.host_report.chart_data, market=self.host_report.market, name=opt[1], do_animation=False)

            Clock.schedule_once(partial(self.save_figure, screen), ix * screenFlipInterval)

        self.generate_report_button.disabled = True

        # Generate report.
        Clock.schedule_once(lambda dt: self.generate_report_from_template(), (nCharts+1)*screenFlipInterval)

    def generate_report_from_template(self):
        # Get current date.
        now = datetime.datetime.now()
        today = now.strftime("%B %d, %Y")

        # Get report-specific data.
        reportAttributes = self.host_report.report_attributes

        ISO = reportAttributes['market area']
        pricing_node = reportAttributes['pricing node']
        ES_device = reportAttributes['selected device']
        revenue_streams = reportAttributes['revenue streams']
        dates_analyzed = reportAttributes['dates analyzed']
        power_rating = reportAttributes['Power_rating']
        energy_capacity = reportAttributes['Energy_capacity']
        storage_efficiency = reportAttributes['Self_discharge_efficiency']
        conversion_efficiency = reportAttributes['Round_trip_efficiency']

        # Retrieve HTML template based on selected ISO.
        template_dir = os.path.join('es_gui', 'resources', 'report_templates')
        output_dir = os.path.join('results', 'valuation', 'report')
        os.makedirs(output_dir, exist_ok=True)

        # Initialize Jinja environment.
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html']))

        if ISO == "ERCOT":
            template = env.get_template('valuation_report_ERCOT.html')
            fname = os.path.join(output_dir, 'QuESt_valuation_report_ERCOT.html')
            
        elif ISO == "MISO":
            template = env.get_template('valuation_report_MISO.html')
            fname = os.path.join(output_dir, 'QuESt_valuation_report_MISO.html')
            
        elif ISO == "PJM":
            template = env.get_template('valuation_report_PJM.html')
            fname = os.path.join(output_dir, 'QuESt_valuation_report_PJM.html')

        elif ISO == "ISONE":
            template = env.get_template('valuation_report_ISONE.html')
            fname = os.path.join(output_dir, 'QuESt_valuation_report_ISONE.html')
        #########################################################################################
        elif ISO == "NYISO":
            template = env.get_template('valuation_report_NYISO.html')
            fname = os.path.join(output_dir, 'QuESt_valuation_report_NYISO.html')
        elif ISO == "SPP":
            template = env.get_template('valuation_report_SPP.html')
            fname = os.path.join(output_dir, 'QuESt_valuation_report_SPP.html')
        elif ISO == "CAISO":
            template = env.get_template('valuation_report_CAISO.html')
            fname = os.path.join(output_dir, 'QuESt_valuation_report_CAISO.html')
        #########################################################################################
        else :
            raise ValueError('The selected ISO does not have a reporting template.')

        # Render output file.
        output = template.render(
					 # GENERAL OUTPUT
					 today=today,
			  		 market_area=ISO,
			  		 header="This report shows the results from optimizations performed by QuESt Valuation.",
			  		 pricing_node=pricing_node,						 
			  		 dates_analyzed=dates_analyzed,
			  		 revenue_streams=revenue_streams,
			  		 ES_device=ES_device,
                     QuESt_Logo=os.path.join('images', 'static', 'Quest_Logo_RGB.png'),
			  		 SNL_image=os.path.join('images', 'static', 'SNL.png'),
			  		 DOE_image=os.path.join('images', 'static', 'DOE.png'),
			  		 acknowledgement="Sandia National Laboratories is a multimission laboratory managed and operated by National Technology & Engineering Solutions of Sandia, LLC, a wholly owned subsidiary of Honeywell International Inc., for the U.S. Department of Energy's National Nuclear Security Administration under contract DE-NA0003525.",
					 # PARAMETER VALUES TABLE
					 power_rating=power_rating,
					 energy_capacity=energy_capacity,
					 storage_efficiency=storage_efficiency,
					 conversion_efficiency=conversion_efficiency,						 
					 # FIGURES
					 revenue_total=self.graphicsLocations['revenue_bar'],
					 revenue_source=self.graphicsLocations['revenue_multisetbar'],
					 activity_total_percent=self.graphicsLocations['activity_donut'],
					 activity_source=self.graphicsLocations['activity_stackedbar_normalized'],
					 activity_source_percent=self.graphicsLocations['activity_stackedbar_normalized']
					 )

        with open(fname,"w") as f:
            f.write(output)
        
        completion_popup = OpenGeneratedReportPopup()
        completion_popup.report_filename = fname
        completion_popup.open()


class OpenGeneratedReportPopup(MyPopup):
    report_filename = ''

    def open_generated_report(self):
        """Opens the generated report and dismisses the popup,"""
        webbrowser.open('file://' + os.path.realpath(self.report_filename))
        self.dismiss()