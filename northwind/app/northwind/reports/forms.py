"""Forms of the Sales and Catalog Reports area (crispy-forms, Bootstrap 5).

The area writes nothing, so its only form takes report criteria: the start and end
dates of the selection page (R-reports-002). It is a GET form whose <form> tag is in
the template, which sends it to the chosen report.
"""

from crispy_forms.helper import FormHelper
from django import forms


class DateInput(forms.DateInput):
    input_type = "date"


class PeriodForm(forms.Form):
    """The selection page's criteria: blank dates take the default period
    (R-reports-003)."""

    start = forms.DateField(label="Start Date", required=False, widget=DateInput())
    end = forms.DateField(label="End Date", required=False, widget=DateInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True
