#!/usr/bin/env python3
"""One-shot fixed-guide processing and honest static-case delivery metadata."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw


BASE = Path(__file__).resolve().parent.parent
SKILL = BASE / "skill-snapshot"
PYTHON = Path(sys.executable)


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cutouts(folder, image, stem, anchor=None, cell=128):
    folder.mkdir(exist_ok=True)
    for name, color in [("light", (238, 237, 229, 255)), ("dark", (33, 40, 49, 255))]:
        canvas = Image.new("RGBA", image.size, color)
        canvas.alpha_composite(image)
        canvas.convert("RGB").save(folder / f"{stem}-{name}-native.png")
        canvas.resize((canvas.width * 2, canvas.height * 2), Image.Resampling.NEAREST).convert("RGB").save(folder / f"{stem}-{name}-2x.png")
    if anchor is not None:
        canvas = Image.new("RGBA", image.size, (70, 79, 73, 255))
        draw = ImageDraw.Draw(canvas)
        ax, ay = anchor
        for x in range(round(ax - cell / 2) % cell, image.width, cell):
            draw.line((x, 0, x, image.height), fill=(126, 144, 126, 255))
        for y in range(round(ay - cell / 2) % cell, image.height, cell):
            draw.line((0, y, image.width, y), fill=(126, 144, 126, 255))
        canvas.alpha_composite(image)
        draw = ImageDraw.Draw(canvas)
        draw.line((ax - 6, ay, ax + 6, ay), fill=(255, 90, 150, 255), width=1)
        draw.line((ax, ay - 6, ax, ay + 6), fill=(255, 90, 150, 255), width=1)
        canvas.convert("RGB").save(folder / f"{stem}-stored-anchor-grid.png")


def process(case):
    p = BASE / case
    guide = json.loads((p / "guide.json").read_text())
    recipe = json.loads((p / "generation-01.json").read_text())
    execution = json.loads((p / "execution.json").read_text())
    authored = json.loads((p / "authored-render/geometry-result.json").read_text())
    kind = "floor" if case == "seamless-square-floor" else "object"
    provenance = {"imageGenerationCalls": 1, "reskinSources": ["source-01.png"],
                  "geometryReferenceRun": "2026-10-17-3d-control-all",
                  "stage": "3d-capture-then-imagegen", "geometryReferenceBundle": "authored-render",
                  "generationRecipe": "generation-01.json", "sourceSHA256": sha(p / "source-01.png")}
    tools = p / "processing-tools"
    tools.mkdir(exist_ok=True)
    processor = "tile_tools.py" if kind == "floor" else "extract_registered_sheet.py"
    shutil.copy2(SKILL / "scripts" / processor, tools / processor)
    if kind == "floor":
        cmd = [str(PYTHON), str(SKILL / "scripts/tile_tools.py"), "floor-material", str(p / "source-01.png"), str(p / "sprites/tile.png")]
    else:
        cmd = [str(PYTHON), str(SKILL / "scripts/extract_registered_sheet.py"), str(p / "source-01.png"), str(p / "guide.json"), str(p / "processed"), "--kind", "object", "--min-alpha", "32"]
    run = subprocess.run(cmd, text=True, capture_output=True)
    execution["processingCommand"] = cmd
    execution["processingExitCode"] = run.returncode
    execution["processingStdout"] = run.stdout
    execution["processingStderr"] = run.stderr
    execution["processingInfo"] = {"processor": f"processing-tools/{processor}", "sha256": sha(tools / processor), "predeclaredMinAlpha": 0 if kind == "floor" else 32, "fitting": False, "clipping": False, "rendererSilhouetteApplied": False, "colorKeyApplied": False}
    if run.returncode:
        error = next((line for line in reversed(run.stderr.splitlines()) if line.strip()), "processing failed")
        result = {"version": 2, "kind": kind, "projection": "top-down-oblique-square-grid", "cellSize": 128,
                  "groundAnchorAlignment": "center", "workflow": "3d-imagegen-reskin", "sprites": [],
                  "processingFailure": {"reason": error, "source": "source-01.png", "guide": "guide.json", "diagnostic": "processing-error.txt", "noFallback": True}, "provenance": provenance}
        (p / "processing-error.txt").write_text(run.stdout + run.stderr)
        execution["processingStatus"] = "failed-source-only"
        execution["processingError"] = error
        image = Image.open(p / "source-01.png").convert("RGBA")
        cutouts(p / "previews", image, "source-only-unregistered")
    elif kind == "floor":
        meta = json.loads((p / "sprites/tile.json").read_text())
        image = Image.open(p / "sprites/tile.png").convert("RGBA")
        result = {"version": 2, "kind": "floor", "projection": "top-down-oblique-square-grid", "cellSize": 128,
                  "groundAnchorAlignment": "center", "workflow": "3d-imagegen-reskin", "sprites": [{"id": case, "image": "sprites/tile.png", "size": [128,128], "anchor": [64,64], "footprint": [128,128], "occupiedCells": [[0,0]], "elevationPx": 0, "artRect": [0,0,128,128], "processing": meta}],
                  "processing": {"method": "uniform-square-resampling", "processor": f"processing-tools/{processor}", "sidecar": "sprites/tile.json", "wholeOpaqueSquare": True, "crop": False}, "provenance": provenance}
        execution["processingStatus"] = "processed"
        execution["processingResult"] = "result.json"
        cutouts(p / "previews", image, case, [64,64])
        for count in [3,5]:
            repeat = Image.new("RGBA", (128*count,128*count))
            for y in range(count):
                for x in range(count): repeat.alpha_composite(image, (x*128,y*128))
            repeat.save(p / f"previews/repeat-{count}-native.png")
            repeat.resize((repeat.width*2, repeat.height*2), Image.Resampling.NEAREST).save(p / f"previews/repeat-{count}-2x.png")
    else:
        result = json.loads((p / "processed/result.json").read_text())
        for collection in ["sprites", "frames"]:
            for item in result[collection]:
                item["image"] = "processed/" + item["image"]
                item["registration"]["guide"] = "guide.json"
                if collection == "sprites":
                    item["id"] = case
                    for key in ["footprint", "occupiedCells", "elevationPx", "baseSize", "groundClearancePx", "supportCells", "overheadCells"]:
                        if key in authored["sprites"][0]: item[key] = authored["sprites"][0][key]
        for key in ["supportCells", "overheadCells"]:
            if key in authored: result[key] = authored[key]
        result["sheet"]["image"] = "processed/" + result["sheet"]["image"]
        result["provenance"]["source"]["path"] = "source-01.png"
        result["provenance"]["guide"]["path"] = "guide.json"
        result["provenance"]["processor"]["path"] = f"processing-tools/{processor}"
        result["provenance"].update(provenance)
        result["workflow"] = "3d-imagegen-reskin"
        result["nominalHeightPx"] = guide["nominalHeightPx"]
        execution["processingStatus"] = "processed"
        execution["processingResult"] = "result.json"
        image = Image.open(p / result["sprites"][0]["image"]).convert("RGBA")
        cutouts(p / "previews", image, case, result["sprites"][0]["anchor"])
    write(p / "result.json", result)
    submission = {"caseId": case, "outputDirectory": str(p), "userPrompt": (p / "request.txt").read_text().rstrip("\n"),
                  "sources": [{"image": "source-01.png", "recipe": "generation-01.json"}], "guide": "guide.json", "guideSHA256": sha(p / "guide.json"), "result": "result.json"}
    write(p / "submission.json", submission)
    execution["resultSHA256"] = sha(p / "result.json")
    execution["submissionSHA256"] = sha(p / "submission.json")
    execution["reviewPreviews"] = [str(x.relative_to(p)) for x in sorted((p / "previews").glob("*.png"))]
    write(p / "execution.json", execution)
    print(case, execution["processingStatus"], execution.get("processingError", ""))


if __name__ == "__main__":
    for case in sys.argv[1:]: process(case)
