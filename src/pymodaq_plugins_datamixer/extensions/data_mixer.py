from qtpy import QtWidgets, QtCore
import numpy as np

from pymodaq_gui import utils as gutils
from pymodaq_utils.config import Config, ConfigError
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_data.data import DataToExport, DataWithAxes

from pymodaq.utils.config import get_set_preset_path
from pymodaq.extensions.utils import CustomExt
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect
from pymodaq_gui.plotting.data_viewers.viewer import ViewerDispatcher

from pymodaq_plugins_datamixer.utils import Config as PluginConfig
from pymodaq_plugins_datamixer.extensions.utils.parser import (
    extract_data_names, split_formulae, replace_names_in_formula)
from pymodaq.control_modules.utils import DAQTypesEnum

logger = set_logger(get_module_name(__file__))

main_config = Config()
plugin_config = PluginConfig()

EXTENSION_NAME = 'Data Mixer'  # the name that will be displayed in the extension list in the
# dashboard
CLASS_NAME = 'DataMixer'  # this should be the name of your class defined below


class DataMixer(CustomExt):
    settings_name = 'DataMixerSettings'
    params = [{'title': 'Edit Formula:', 'name': 'edit_formula', 'type': 'text', 'value': ''}]
    dte_computed_signal = QtCore.Signal(DataToExport)

    def __init__(self, parent: gutils.DockArea, dashboard):
        super().__init__(parent, dashboard)

        self.data0D_list_widget = ItemSelect()
        self.data1D_list_widget = ItemSelect()
        self.data2D_list_widget = ItemSelect()
        self.dataND_list_widget = ItemSelect()

        self.setup_ui()

    def setup_docks(self):
        """Mandatory method to be subclassed to setup the docks layout

        """
        self.docks['settings'] = gutils.Dock('Settings')
        self.dockarea.addDock(self.docks['settings'])
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.docks['settings'].addWidget(splitter)
        splitter.addWidget(self.modules_manager.settings_tree)
        self.modules_manager.tree.header().setVisible(False)
        self.modules_manager.settings.child('modules', 'actuators').hide()
        self.modules_manager.settings.child('move_done').hide()
        self.modules_manager.settings.child('det_done').hide()
        self.modules_manager.settings.child('data_dimensions',
                                            'det_data_list0D').setOpts(height=150)
        self.modules_manager.settings.child('data_dimensions').hide()
        self.modules_manager.settings.child('actuators_positions').hide()

        splitter.addWidget(self.settings_tree)

        self.docks['data'] = gutils.Dock('Data List')
        self.dockarea.addDock(self.docks['data'], 'right')
        widget_data = QtWidgets.QWidget()
        widget_data.setLayout(QtWidgets.QVBoxLayout())
        self.docks['data'].addWidget(widget_data)
        widget_data.layout().addWidget(QtWidgets.QLabel('Data0D:'))
        widget_data.layout().addWidget(self.data0D_list_widget)
        widget_data.layout().addWidget(QtWidgets.QLabel('Data1D:'))
        widget_data.layout().addWidget(self.data1D_list_widget)
        widget_data.layout().addWidget(QtWidgets.QLabel('Data2D:'))
        widget_data.layout().addWidget(self.data2D_list_widget)
        widget_data.layout().addWidget(QtWidgets.QLabel('DataND:'))
        widget_data.layout().addWidget(self.dataND_list_widget)

        self.docks['computed'] = gutils.Dock('Computed data')
        self.dockarea.addDock(self.docks['computed'], 'right')

        self.area_computed = gutils.DockArea()
        self.docks['computed'].addWidget(self.area_computed)

        self.dte_computed_viewer = ViewerDispatcher(self.area_computed)

    def setup_actions(self):
        """Method where to create actions to be subclassed. Mandatory
        """
        self.add_action('quit', 'Quit', 'close2', "Quit program")
        self.add_action('get_data', 'Get Data List', 'properties',
                        "Get the list of data from selected detectors")
        self.add_action('compute', 'Compute Formulae', 'algo',
                        'Compute the Formula when new data is available',
                        checkable=True)
        self.add_action('snap', 'Snap Detectors', 'snap',
                        'Snap all selected detectors')
        self.add_action('create_computed_detectors', 'Create Computed Detectors', 'Add_Step',
                        tip='Create a DAQ_Viewer Control Module')

    def connect_things(self):
        """Connect actions and/or other widgets signal to methods"""
        self.connect_action('quit', self.quit)
        self.connect_action('get_data', self.show_data_list)
        self.modules_manager.det_done_signal.connect(self.process_data)
        self.dte_computed_signal.connect(self.plot_formulae_results)
        self.connect_action('snap', self.snap)
        self.modules_manager.detectors_changed.connect(self.update_connect_detectors)
        self.connect_action('create_computed_detectors', self.create_computed_detectors)

    def setup_menu(self):
        """Non mandatory method to be subclassed in order to create a menubar

        create menu for actions contained into the self._actions, for instance:

        Examples
        --------
        >>>file_menu = self.mainwindow.menuBar().addMenu('File')
        >>>self.affect_to('load', file_menu)
        >>>self.affect_to('save', file_menu)

        >>>file_menu.addSeparator()
        >>>self.affect_to('quit', file_menu)

        See Also
        --------
        pymodaq.utils.managers.action_manager.ActionManager
        """
        # todo create and populate menu using actions defined above in self.setup_actions
        pass

    def value_changed(self, param):
        """ Actions to perform when one of the param's value in self.settings is changed from the
        user interface

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        """
        pass

    def quit(self):
        self.mainwindow.close()

    def snap(self):
        self.modules_manager.grab_data()

    def create_computed_detectors(self):
        # Now that we have the module manager, load PID if it is checked in managers
        try:
            detector_modules = []
            self.dashboard.add_det('DataMixer', None, [], [], detector_modules,
                                   plug_type=DAQTypesEnum.DAQ0D.name,
                                   plug_subtype='DataMixer')
            self.dashboard.add_det_from_extension('DataMixer', 'DAQ0D', 'DataMixer', self)
            self.set_action_enabled('create_computed_detectors', False)
        except Exception as e:
            logger.exception(str(e))
            pass

    def update_connect_detectors(self):
        try:
            self.connect_detectors(False)
        except :
            pass
        self.connect_detectors()

    def connect_detectors(self, connect=True):
        """Connect detectors to DAQ_Logging do_save_continuous method

        Parameters
        ----------
        connect: bool
            If True make the connection else disconnect
        """
        self.modules_manager.connect_detectors(connect=connect)

    def plot_formulae_results(self, dte):
        self.dte_computed_viewer.show_data(dte)

    def process_data(self, dte: DataToExport):
        if self.is_action_checked('compute'):
            formulae = split_formulae(self.get_formulae())
            dte_processed = DataToExport('Computed')
            for ind, formula in enumerate(formulae):
                try:
                    dwa = self.compute_formula(formula, dte,
                                               name=f'Formula_{ind:03.0f}')
                    dte_processed.append(dwa)
                except Exception as e:
                    pass
            self.dte_computed_signal.emit(dte_processed)

    def compute_formula(self, formula: str, dte: DataToExport,
                        name: str) -> DataWithAxes:
        """ Compute the operations in formula using data stored in dte

        Parameters
        ----------
        formula: str
            The mathematical formula using numpy and data fullnames within curly brackets
        dte: DataToExport
        name: str
            The name to give to the produced DataWithAxes

        Returns
        -------
        DataWithAxes: the results of the formula computation
        """
        formula_to_eval, names = replace_names_in_formula(formula)
        dwa = eval(formula_to_eval)
        dwa.name = name
        return dwa

    def get_formulae(self) -> str:
        """ Read the content of the formula QTextEdit widget"""
        return self.settings['edit_formula']

    def show_data_list(self):
        dte = self.modules_manager.get_det_data_list()

        data_list0D = dte.get_full_names('data0D')
        data_list1D = dte.get_full_names('data1D')
        data_list2D = dte.get_full_names('data2D')
        data_listND = dte.get_full_names('dataND')

        self.data0D_list_widget.set_value(dict(all_items=data_list0D, selected=[]))
        self.data1D_list_widget.set_value(dict(all_items=data_list1D, selected=[]))
        self.data2D_list_widget.set_value(dict(all_items=data_list2D, selected=[]))
        self.dataND_list_widget.set_value(dict(all_items=data_listND, selected=[]))


def main():
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

    app = mkQApp('DataMixer')

    preset_file_name = plugin_config('preset')
    dashboard, extension, win = load_dashboard_with_preset(preset_file_name, EXTENSION_NAME)
    app.exec()

    return dashboard, extension, win


if __name__ == '__main__':
    main()
