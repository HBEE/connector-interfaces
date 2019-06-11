# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 initOS GmbH & Co. KG (<http://www.initos.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import csv
import io

from odoo import api, models

from .abstract_task import AbstractChunkReadTask


class CsvExport(AbstractChunkReadTask):
    "Reads a chunk and writes it into a CSV file"

    def read_chunk(self, config=None, chunk_data=None, delay=True):
        if not chunk_data:
            return

        # output encoding defaults to utf-8
        encoding = config.get('encoding', 'utf-8')

        def encode_value(value):
            if isinstance(value, str):
                return value.encode(encoding)
            return value

        data = io.StringIO()
        writer = csv.writer(data)
        for row in chunk_data:
            writer.writerow(list(map(encode_value, row)))

        file_id = self.create_file(config.get('filename'), data.getvalue())
        result = self.run_successor_tasks(file_id=file_id, delay=delay)
        if result:
            return result
        return file_id


class CsvExportTask(models.Model):
    _inherit = 'impexp.task'

    @api.model
    def _get_available_tasks(self):
        return super()._get_available_tasks() + [('csv_export', 'CSV Export')]

    def csv_export_class(self):
        return CsvExport
