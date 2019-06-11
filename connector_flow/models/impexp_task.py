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

import ast

from odoo import _, api, exceptions, fields, models
from odoo.addons.queue_job.job import job, related_action


class ImpExpTaskTransition(models.Model):
    _name = 'impexp.task.transition'
    _description = 'Transition between tasks'

    task_from_id = fields.Many2one('impexp.task',
                                   string='Output-producing Task')
    task_to_id = fields.Many2one('impexp.task', string='Input-consuming Task')


class ImpExpTaskFlow(models.Model):
    _name = 'impexp.task.flow'
    _description = 'A flow of tasks that are connected by transitions'

    name = fields.Char(required=True)
    task_ids = fields.One2many('impexp.task', 'flow_id',
                               string='Tasks in Flow')


class ImpExpTask(models.Model):
    _name = 'impexp.task'
    _description = 'A wrapper class for an import/export task'

    @api.model
    def _get_available_tasks(self):
        return []

    name = fields.Char(required=True)
    task = fields.Selection(selection='_get_available_tasks')
    config = fields.Text(string='Configuration')
    last_start = fields.Datetime(string='Starting Time of the Last Run')
    last_finish = fields.Datetime(string='Finishing Time of the '
                                         'Last Successful Run')
    max_retries = fields.Integer(string='Maximal Number of Re-tries'
                                        ' If Run Asynchronously',
                                 required=True, default=1)
    flow_id = fields.Many2one('impexp.task.flow', string='Task Flow')
    transitions_out_ids = fields.One2many('impexp.task.transition',
                                          'task_from_id',
                                          string='Outgoing Transitions')
    transitions_in_ids = fields.One2many('impexp.task.transition',
                                         'task_to_id',
                                         string='Incoming Transitions')
    flow_start = fields.Boolean(string='Start of a Task Flow')

    @api.multi
    @api.constrains('flow_start', 'flow_id')
    def _check_unique_flow_start(self):
        """Check that there is at most one task that starts the
           flow in a task flow"""
        for rec in self.filtered('flow_start'):
            flow_start_count = self.search_count([
                ('flow_id', '=', rec.flow_id.id),
                ('flow_start', '=', True),
            ])
            if flow_start_count > 1:
                raise exceptions.ValidationError(
                    _('The start of a task flow has to be unique'))

    @api.multi
    def _config(self):
        """Parse task configuration"""
        self.ensure_one()
        config = self.config
        if config:
            return ast.literal_eval(config)
        return {}

    @api.multi
    def do_run(self, delay=True, **kwargs):
        self.ensure_one()
        if delay:
            method = self.with_delay().run_task
            kwargs.update({'description': self.name,
                           'max_retries': self.max_retries})
        else:
            method = self.run_task
        result = method(delay=delay, **kwargs)
        # If we run delayhronously, we ignore the result
        #  (which is the UUID of the job in the queue).
        if not delay:
            return result

    @api.model
    def do_run_flow(self, flow_id, **kwargs):
        flow = self.env['impexp.task.flow'].browse(flow_id)
        flow.ensure_one()
        start_task = False
        for task in flow.task_ids:
            if task.flow_start:
                start_task = task
                break
        if not start_task:
            raise Exception(_('Flow %d has no start') % flow_id)
        return start_task.do_run(**kwargs)

    @api.multi
    def get_task_instance(self):
        self.ensure_one()
        task_method = self.task
        task_class = getattr(self, task_method + '_class')()
        return task_class(self.env, self.ids)

    @job
    @related_action(action='related_action_impexp_task')
    @api.multi
    def run_task(self, **kwargs):
        self.ensure_one()
        task_instance = self.get_task_instance()
        config = self._config()
        return task_instance.run(config=config, **kwargs)
