"""Small deterministic stdlib PEP517 wheel-only backend, no package execution."""
import base64
import csv
import hashlib
import io
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = ["__init__.py", "api.py", "output_types.py", "output_projection.py", "simulation.py", "synthetic_catalog.py", "reporting.py", "cli.py", "__main__.py", "_r4/__init__.py",
           "_r4/domain.py", "_r4/oracle.py", "_r4/flow_types.py", "_r4/state_model.py",
           "_r4/quantization_types.py", "_r4/request_quantizer.py", "_r4/normalized_pipeline.py",
           "provenance/derived_modules.json", "trace_analysis.py", "report_csv.py", "report_html.py", "trace_report.py"]


def get_requires_for_build_wheel(config_settings=None):
    return []


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    distribution, version = project["name"].replace("-", "_"), project["version"]
    dist_info = f"{distribution}-{version}.dist-info"
    files = {"cyberlateral_dev/" + name: (ROOT / "src/cyberlateral_dev" / name).read_bytes() for name in PAYLOAD}
    files[dist_info + "/METADATA"] = (
        "Metadata-Version: 2.4\n" + f"Name: {project['name']}\nVersion: {version}\n" +
        f"Summary: {project['description']}\nRequires-Python: {project['requires-python']}\n" +
        "License-File: openpilot.LICENSE\nLicense-File: opendbc.LICENSE\n\n"
    ).encode()
    files[dist_info + "/WHEEL"] = b"Wheel-Version: 1.0\nGenerator: cyberlateral-dev-stdlib\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    for name in ["openpilot.LICENSE", "opendbc.LICENSE"]:
        files[dist_info + "/licenses/" + name] = (ROOT / "licenses" / name).read_bytes()
    record_name = dist_info + "/RECORD"
    rows = io.StringIO(newline="")
    writer = csv.writer(rows, lineterminator="\n")
    for name, raw in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + digest, len(raw)])
    writer.writerow([record_name, "", ""])
    files[record_name] = rows.getvalue().encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    directory = Path(wheel_directory)
    directory.mkdir(parents=True, exist_ok=True)
    wheel_name = f"{distribution}-{version}-py3-none-any.whl"
    with (directory / wheel_name).open("xb") as stream:
        stream.write(output.getvalue())
    return wheel_name
