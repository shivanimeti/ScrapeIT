import os
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.contrib import messages
from .forms import SearchForm, UploadCSVForm
from .utils import (
    search_duckduckgo, 
    write_search_results_to_csv, 
    read_urls_from_csv, 
    extract_contact_info, 
    write_contact_info_to_csv,
    filter_search_results,
    extract_contact_info_batch
)

def search_view(request):
    """
    View for searching products by keyword, location, and country
    """
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            keyword = form.cleaned_data['keyword']
            location = form.cleaned_data['location']
            country = form.cleaned_data['country']
            
            # Get filter options but don't apply them yet
            shopify_only = form.cleaned_data.get('shopify_only', False)
            fast_loading = form.cleaned_data.get('fast_loading', False)
            active_only = form.cleaned_data.get('active_only', False)
            
            # Perform search
            results = search_duckduckgo(keyword, location, country)
            
            # Store the filter options but don't apply them yet
            request.session['search_filters'] = {
                'shopify_only': shopify_only,
                'fast_loading': fast_loading,
                'active_only': active_only
            }
            
            if results:
                # Write results to CSV
                csv_file = write_search_results_to_csv(results)
                if csv_file:
                    # Store the results in session for display
                    request.session['search_results'] = results
                    request.session['csv_filename'] = csv_file
                    return redirect('search_results')
                else:
                    messages.error(request, "Failed to generate CSV file.")
            else:
                messages.warning(request, "No search results found.")
    else:
        form = SearchForm()
    
    return render(request, 'home/search.html', {'form': form})

def search_results_view(request):
    """
    View for displaying search results and providing CSV download
    """
    results = request.session.get('search_results', [])
    csv_filename = request.session.get('csv_filename', None)
    
    context = {
        'results': results,
        'csv_filename': csv_filename,
    }
    
    return render(request, 'home/search_results.html', context)

def download_csv(request):
    """
    View for downloading the generated CSV file
    """
    csv_filename = request.session.get('csv_filename', None)
    
    if csv_filename and os.path.exists(csv_filename):
        response = FileResponse(open(csv_filename, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(csv_filename)}"'
        return response
    
    messages.error(request, "CSV file not found.")
    return redirect('search')

def upload_csv_view(request):
    """
    View for uploading CSV file to extract contact information
    """
    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Check file extension
            if not csv_file.name.endswith('.csv'):
                messages.error(request, "Please upload a CSV file.")
                return render(request, 'home/upload_csv.html', {'form': form})
            
            # Read the first few bytes to check if it's a valid file
            sample = csv_file.read(1024)
            csv_file.seek(0)
            
            # Debug info
            print(f"File name: {csv_file.name}, Size: {csv_file.size} bytes")
            print(f"Sample content: {sample[:100]}")
            
            # Read URLs from CSV
            urls = read_urls_from_csv(csv_file)
            
            if urls:
                # Store URLs in session for processing
                request.session['urls_to_process'] = urls
                messages.success(request, f"Found {len(urls)} URLs to process.")
                return redirect('process_urls')
            else:
                messages.error(request, "No valid URLs found in the CSV file. Please check the file format and content.")
                
                # Add debug info to the context
                debug_context = {
                    'form': form,
                    'debug_info': True,
                    'file_name': csv_file.name,
                    'file_size': csv_file.size
                }
                return render(request, 'home/upload_csv.html', debug_context)
    else:
        form = UploadCSVForm()
    
    return render(request, 'home/upload_csv.html', {'form': form})

def process_urls_view(request):
    """
    View for processing URLs and extracting contact information
    """
    urls = request.session.get('urls_to_process', [])
    
    if not urls:
        return redirect('upload_csv')
    
    # Use the existing extract_contact_info_batch function from utils.py
    # which already implements parallel processing
    from .utils import extract_contact_info_batch
    contact_info_list = extract_contact_info_batch(urls)
    
    # Write contact information to CSV
    csv_file = write_contact_info_to_csv(contact_info_list)
    
    if csv_file:
        request.session['contact_info'] = contact_info_list
        request.session['contact_csv_filename'] = csv_file
        return redirect('contact_results')
    else:
        return redirect('upload_csv')

def contact_results_view(request):
    """
    View for displaying contact information results
    """
    contact_info = request.session.get('contact_info', [])
    csv_filename = request.session.get('contact_csv_filename', None)
    
    context = {
        'contact_info': contact_info,
        'csv_filename': csv_filename,
    }
    
    return render(request, 'home/contact_results.html', context)

def download_contact_csv(request):
    """
    View for downloading the contact information CSV file
    """
    csv_filename = request.session.get('contact_csv_filename', None)
    
    if csv_filename and os.path.exists(csv_filename):
        response = FileResponse(open(csv_filename, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(csv_filename)}"'
        return response
    
    messages.error(request, "Contact CSV file not found.")
