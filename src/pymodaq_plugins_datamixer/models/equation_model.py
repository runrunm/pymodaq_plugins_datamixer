from pymodaq_plugins_datamixer.extensions.utils.model import DataMixerModel

from pymodaq_data.data import DataToExport, DataWithAxes

from pymodaq_plugins_datamixer.extensions.utils.parser import (
    extract_data_names, split_formulae, replace_names_in_formula)


class DataMixerModelEquation(DataMixerModel):
    param = [
        {'title': 'Edit Formula:', 'name': 'edit_formula', 'type': 'text', 'value': ''},
        {'title': 'Data0D:', 'name': 'data0D', 'type': 'item_select',
         'value': dict(all_items=[], selected=[])},
        {'title': 'Data1D:', 'name': 'data1D', 'type': 'item_select',
         'value': dict(all_items=[], selected=[])},
        {'title': 'Data2D:', 'name': 'data2D', 'type': 'item_select',
         'value': dict(all_items=[], selected=[])},


    ]

    pass


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

    def process_dte(self, dte: DataToExport):
        formulae = split_formulae(self.get_formulae())
        dte_processed = DataToExport('Computed')
        for ind, formula in enumerate(formulae):
            try:
                dwa = self.compute_formula(formula, dte,
                                           name=f'Formula_{ind:03.0f}')
                dte_processed.append(dwa)
            except Exception as e:
                pass
        return dte_processed

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

