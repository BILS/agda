from django import forms

class SpeciesGeoCoderForm(forms.Form):
    name = forms.CharField(max_length=100, initial='SpeciesGeoCoder job', help_text='Job name')
    #query = forms.CharField(widget=forms.Textarea(attrs={'class': 'query-sequence'}),
    #                        help_text='One or more fasta format sequences',
    #                        required=False)
    localities = forms.FileField(
            help_text='',
            label='Localities', 
            required=True)
    polygons = forms.FileField(
            help_text='',
            label='Polygons', 
            required=True)
