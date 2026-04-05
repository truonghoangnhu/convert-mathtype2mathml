import threading
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BatchUploadForm, RegisterForm, SingleUploadForm
from .models import Conversion
from .services import run_conversion


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("dashboard")
    else:
        form = RegisterForm()
    return render(request, "converter/register.html", {"form": form})


@login_required
def dashboard_view(request):
    recent = Conversion.objects.filter(user=request.user)[:10]
    upload_form = SingleUploadForm()
    batch_form = BatchUploadForm()
    return render(request, "converter/dashboard.html", {
        "recent": recent,
        "upload_form": upload_form,
        "batch_form": batch_form,
    })


@login_required
def upload_view(request):
    if request.method != "POST":
        return redirect("dashboard")

    form = SingleUploadForm(request.POST, request.FILES)
    if form.is_valid():
        f = form.cleaned_data["docx_file"]
        conversion = Conversion.objects.create(
            user=request.user,
            original_filename=f.name,
            docx_file=f,
            use_transpect=form.cleaned_data["use_transpect"],
        )
        thread = threading.Thread(target=run_conversion, args=(conversion,))
        thread.start()
        messages.info(request, f"Converting {f.name}...")
        return redirect("conversion_detail", pk=conversion.pk)

    messages.error(request, "Invalid file upload.")
    return redirect("dashboard")


@login_required
def batch_upload_view(request):
    if request.method != "POST":
        return redirect("dashboard")

    files = request.FILES.getlist("docx_files")
    if not files:
        messages.error(request, "No files selected.")
        return redirect("dashboard")

    use_transpect = request.POST.get("use_transpect") == "on"
    conversions = []

    for f in files:
        if not f.name.lower().endswith(".docx"):
            messages.warning(request, f"Skipped {f.name} (not .docx)")
            continue
        if f.size > 50 * 1024 * 1024:
            messages.warning(request, f"Skipped {f.name} (too large)")
            continue

        conversion = Conversion.objects.create(
            user=request.user,
            original_filename=f.name,
            docx_file=f,
            use_transpect=use_transpect,
        )
        conversions.append(conversion)
        thread = threading.Thread(target=run_conversion, args=(conversion,))
        thread.start()

    messages.info(request, f"Started converting {len(conversions)} file(s).")
    return redirect("history")


@login_required
def history_view(request):
    conversions = Conversion.objects.filter(user=request.user)
    return render(request, "converter/history.html", {"conversions": conversions})


@login_required
def conversion_detail_view(request, pk):
    conversion = get_object_or_404(Conversion, pk=pk, user=request.user)
    html_content = None
    if conversion.status == Conversion.Status.COMPLETED and conversion.html_file:
        try:
            with open(conversion.html_file.path, "r", encoding="utf-8") as f:
                html_content = f.read()
        except FileNotFoundError:
            html_content = None
    return render(request, "converter/detail.html", {
        "conversion": conversion,
        "html_content": html_content,
    })


@login_required
def download_view(request, pk):
    conversion = get_object_or_404(Conversion, pk=pk, user=request.user)
    if not conversion.html_file:
        raise Http404("No output file available.")
    return FileResponse(
        open(conversion.html_file.path, "rb"),
        as_attachment=True,
        filename=conversion.original_filename.replace(".docx", ".html"),
    )
