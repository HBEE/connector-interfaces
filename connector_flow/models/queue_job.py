# -*- coding: utf-8 -*-
# Copyright 2017 Versada UAB
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class QueueJob(models.Model):
    _inherit = 'queue.job'

    @api.multi
    def related_action_impexp_task(self, **kwargs):
        self.ensure_one()
        model = self.env[self.model_name]
        task_instance = model.browse(self.record_ids).get_task_instance()
        return task_instance.related_action(job=self, **kwargs)
