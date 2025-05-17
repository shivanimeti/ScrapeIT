from django import forms
import requests

def get_country_choices():
    """Get list of countries from REST Countries API"""
    try:
        response = requests.get('https://restcountries.com/v3.1/all?fields=name,cca2')
        countries = response.json()
        # Sort countries by name
        countries.sort(key=lambda x: x['name']['common'])
        # Create choices list with country code as value and common name as display
        choices = [('', 'Select a country')] + [(country['name']['common'], country['name']['common']) for country in countries]
        return choices
    except Exception:
        # Fallback list of common countries if API fails
        return [
            ('', 'Select a country'),
            ('United States', 'United States'),
            ('Canada', 'Canada'),
            ('United Kingdom', 'United Kingdom'),
            ('Australia', 'Australia'),
            ('Germany', 'Germany'),
            ('France', 'France'),
            ('Japan', 'Japan'),
            ('China', 'China'),
            ('India', 'India'),
            ('Brazil', 'Brazil'),
        ]

class SearchForm(forms.Form):
    country = forms.ChoiceField(
        choices=get_country_choices,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary',
        })
    )
    location = forms.CharField(
        max_length=100, 
        required=True, 
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary',
            'placeholder': 'Enter state/city'
        })
    )
    keyword = forms.CharField(
        max_length=255, 
        required=True, 
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary',
            'placeholder': 'Enter product keyword'
        })
    )
    
    # Search filters
    shopify_only = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded'
        }),
        label="Shopify sites only"
    )
    fast_loading = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded'
        }),
        label="Fast loading sites only (< 5 sec)"
    )
    active_only = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded'
        }),
        label="Active websites only"
    )

class UploadCSVForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'file-input',
            'accept': '.csv'
        })
    )


