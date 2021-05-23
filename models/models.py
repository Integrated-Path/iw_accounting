# -*- coding: utf-8 -*-

from odoo import models, fields, api
import calendar
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError

class accounting_assets(models.Model):
    _inherit = "account.asset.asset"

    is_calculate_days = fields.Boolean(string="Calculate Days")
    
    def _compute_board_amount(self, sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, spacial_state=False, index=0):
        amount = 0

        # last depreciation
        if sequence == undone_dotation_number:
            amount = residual_amount

            # custom line
            if self.is_calculate_days:
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
            
        else:
            if self.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))

                # custome function
                if self.is_calculate_days and spacial_state == 'first':
                    one_peroid = self.method_period
                    # fetching the start of the first depreciation
                    start_of_first_period = depreciation_date - relativedelta(months=one_peroid)
                    if start_of_first_period < self.date and index == 0:
                        total_days = depreciation_date - start_of_first_period
                        skipped_days = self.date - start_of_first_period
                        registered_days = total_days - skipped_days
                        amount *= registered_days / total_days

                if self.is_calculate_days and spacial_state == 'last':
                    amount = residual_amount
                    # raise UserError( str(residual_amount) )
                
                if self.prorata:
                    amount = amount_to_depr / self.method_number
            elif self.method == 'degressive':
                amount = residual_amount * self.method_progress_factor
            if self.prorata and sequence == 1:
                amount = self._calculate_prorated_amount(self.date,
                                                        depreciation_date, 
                                                        amount,
                                                        self.method_period)
        return amount

    
    @api.multi
    def compute_depreciation_board(self):
        
        self.ensure_one()

        posted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: x.move_check).sorted(key=lambda l: l.depreciation_date)
        unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: not x.move_check)

        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

        if self.value_residual != 0.0:
            amount_to_depr = residual_amount = self.value_residual

            # if we already have some previous validated entries, starting date is last entry + method period
            if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
                last_depreciation_date = fields.Date.from_string(posted_depreciation_line_ids[-1].depreciation_date)
                depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
            else:
                # depreciation_date computed from the purchase date
                depreciation_date = self.date
                if self.date_first_depreciation == 'last_day_period':
                    # depreciation_date = the last day of the month
                    depreciation_date = depreciation_date + relativedelta(day=31)
                    # ... or fiscalyear depending the number of period
                    if self.method_period == 12:
                        depreciation_date = depreciation_date + relativedelta(month=self.company_id.fiscalyear_last_month)
                        depreciation_date = depreciation_date + relativedelta(day=self.company_id.fiscalyear_last_day)
                        if depreciation_date < self.date:
                            depreciation_date = depreciation_date + relativedelta(years=1)
                elif self.first_depreciation_manual_date and self.first_depreciation_manual_date != self.date:
                    # depreciation_date set manually from the 'first_depreciation_manual_date' field
                    depreciation_date = self.first_depreciation_manual_date


            total_days = 366 if calendar.isleap(depreciation_date.year) else 365
            month_day = depreciation_date.day
            undone_dotation_number = self._compute_board_undone_dotation_nb(depreciation_date, total_days)

            # custom
            range_end = undone_dotation_number
            if self.is_calculate_days:
                range_end += 1

            lines_range = range(len(posted_depreciation_line_ids), range_end)
            
            for x in lines_range:
                sequence = x + 1

                # custome
                if self.is_calculate_days and x == 0:
                    spacial_state = 'first'
                elif self.is_calculate_days and x == lines_range[-1]:
                    spacial_state = 'last'
                else:
                    spacial_state = False

                amount = self._compute_board_amount(sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, spacial_state=spacial_state, index=x)
                amount = self.currency_id.round(amount)
                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    continue
                residual_amount -= amount
                vals = {
                    'amount': amount,
                    'asset_id': self.id,
                    'sequence': sequence,
                    'name': (self.code or '') + '/' + str(sequence),
                    'remaining_value': residual_amount,
                    'depreciated_value': self.value - (self.salvage_value + residual_amount),
                    'depreciation_date': depreciation_date,
                }
                commands.append((0, False, vals))

                previous_depreciation_date = depreciation_date
                depreciation_date = depreciation_date + relativedelta(months=+self.method_period)

                if month_day > 28 and self.date_first_depreciation == 'manual':
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=min(max_day_in_month, month_day))

                # datetime doesn't take into account that the number of days is not the same for each month
                if self.method_period % 12 != 0 and self.date_first_depreciation == 'last_day_period':
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=max_day_in_month)

        self.write({'depreciation_line_ids': commands})

        return True
