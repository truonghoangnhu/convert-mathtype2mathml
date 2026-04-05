import subprocess
import shutil
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from .models import Conversion


def run_conversion(conversion: Conversion):
    """Run the Java converter on a single docx file."""
    conversion.status = Conversion.Status.PROCESSING
    conversion.save(update_fields=["status"])

    try:
        docx_path = Path(conversion.docx_file.path)
        output_dir = Path(settings.MEDIA_ROOT) / "outputs" / str(conversion.user.id) / conversion.id.hex
        output_dir.mkdir(parents=True, exist_ok=True)

        html_filename = docx_path.stem + ".html"
        html_path = output_dir / html_filename

        jar_path = settings.JAR_PATH

        if not jar_path.exists():
            raise FileNotFoundError(f"JAR not found: {jar_path}")

        cmd = [
            "java", "-jar", str(jar_path),
            str(docx_path),
            str(html_path),
        ]

        if conversion.use_transpect:
            work_dir = output_dir / "transpect_work"
            work_dir.mkdir(parents=True, exist_ok=True)

            sidecar_script = settings.BASE_DIR / "scripts" / "transpect" / "generate_sidecars.sh"
            mt_dir = settings.TRANSPECT_MT_DIR
            xmlcalabash_jar = settings.XMLCALABASH_JAR
            saxon_jar = settings.SAXON_HE_JAR

            if sidecar_script.exists() and mt_dir.exists():
                sidecar_cmd = [
                    "bash", str(sidecar_script),
                    str(docx_path),
                    str(work_dir),
                    str(mt_dir),
                    str(xmlcalabash_jar),
                    str(saxon_jar),
                ]
                subprocess.run(
                    sidecar_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=False,
                )

                manifest = work_dir / "manifest.tsv"
                if manifest.exists():
                    cmd.extend(["--mathml-manifest", str(manifest)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=True,
        )

        if html_path.exists():
            rel_path = html_path.relative_to(settings.MEDIA_ROOT)
            conversion.html_file.name = str(rel_path)
            conversion.status = Conversion.Status.COMPLETED
            conversion.completed_at = timezone.now()
        else:
            conversion.status = Conversion.Status.FAILED
            conversion.error_message = "HTML output file was not created."

    except subprocess.TimeoutExpired:
        conversion.status = Conversion.Status.FAILED
        conversion.error_message = "Conversion timed out (10 min limit)."
    except subprocess.CalledProcessError as e:
        conversion.status = Conversion.Status.FAILED
        conversion.error_message = f"Converter error:\n{e.stderr[:2000]}"
    except Exception as e:
        conversion.status = Conversion.Status.FAILED
        conversion.error_message = str(e)[:2000]

    conversion.save()
