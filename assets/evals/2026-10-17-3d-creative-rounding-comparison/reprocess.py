#!/usr/bin/env python3
"""Reprocess preserved original AI canvases; never generate, fit, or grade art.

Run once after prepare_evals.py creates this two-case run. Existing extraction
directories cause failure so subsequent attempts cannot overwrite the evidence.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parent
ORIGINAL_ID = "2026-10-17-3d-creative-reskin-all"
ORIGINAL = ROOT.parent / ORIGINAL_ID
CASES = ("lava-tile", "seated-character-separated")
SCRIPTS = ROOT / "skill-snapshot/scripts"
COMMANDS = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(args, log):
    command = [sys.executable, *map(str, args)]
    completed = subprocess.run(command, cwd=ROOT.parents[2], capture_output=True, text=True)
    record = {"command": command, "cwd": str(ROOT.parents[2]),
              "exitCode": completed.returncode, "stdout": completed.stdout,
              "stderr": completed.stderr}
    COMMANDS.append(record)
    write(log, record)
    if completed.returncode:
        raise RuntimeError(f"Processing failed; retain diagnostic {log}: {completed.stderr}")


def copy_evidence(case_id):
    source, destination = ORIGINAL / case_id, ROOT / case_id
    preserved = []
    # These are unchanged generation inputs and their authored geometry. All
    # previous delivery/processing metadata is separately labeled as historical.
    for path in sorted(source.iterdir()):
        name = path.name
        direct = (name.startswith("source-") or name.startswith("generation-") or
                  name in ("guide.json", "guides", "references", "authored-render", "geometry-reference"))
        if direct:
            target = destination / name
        elif name == "request.txt":
            target = destination / "provenance/original-case-metadata/request.txt"
        elif name == "previews":
            recipe = path / "preview-recipe.json"
            if recipe.exists():
                target = destination / "provenance/original-case-metadata/preview-recipe.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(recipe, target)
                preserved.append({"original": str(recipe), "copy": target.relative_to(destination).as_posix(), "sha256": sha(recipe)})
            continue
        elif name in ("execution.json", "result.json", "submission.json", "processing-error.txt",
                      "processing-tools", "art", "provenance"):
            target = destination / "provenance/original-case-metadata" / name
        else:
            # Old normalized outputs are not comparison inputs; both layers
            # must be independently extracted with the new frozen processor.
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            pairs = [(p, target / p.relative_to(path)) for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
        else:
            shutil.copy2(path, target)
            pairs = [(path, target)]
        for original, copied in pairs:
            assert original.read_bytes() == copied.read_bytes()
            preserved.append({"original": str(original), "copy": copied.relative_to(destination).as_posix(), "sha256": sha(original)})
    write(destination / "provenance/reused-source.json", {
        "reusedSourceRun": ORIGINAL_ID, "reusedSourceCase": case_id,
        "thisProcessingRunImageGenerationCalls": 0,
        "originalImageGenerationCalls": 1 if case_id == "lava-tile" else 2,
        "generationRecipes": "Exact original bytes, including prompts and actual original tool-call reference paths; their processing fields describe the historical run only",
        "preservedFiles": preserved,
        "previousProcessedPNGsCopied": False,
        "previousPreviewsOrReviewsCopied": False,
    })


def provenance(case_id):
    original = read(ORIGINAL / case_id / "result.json")["provenance"]
    result = copy.deepcopy(original)
    result.pop("imageGenerationCalls", None)
    result.update(reusedSourceRun=ORIGINAL_ID,
                  originalImageGenerationCalls=1 if case_id == "lava-tile" else 2,
                  thisProcessingRunImageGenerationCalls=0,
                  reskinSources=[f"source-{i:02}.png" for i in range(1, 2 if case_id == "lava-tile" else 3)],
                  originalReskinSources=[str(ORIGINAL / case_id / f"source-{i:02}.png") for i in range(1, 2 if case_id == "lava-tile" else 3)],
                  processingRun=ROOT.name,
                  originalGenerationMetadata="provenance/original-case-metadata",
                  reuseRecord="provenance/reused-source.json")
    if "geometryReference" in result:
        result["geometryReference"] = "provenance/original-case-metadata/provenance/reused-geometry.json"
    return result


def extract(case_id, source, guide, output):
    directory = ROOT / case_id
    run([SCRIPTS / "extract_registered_sheet.py", directory / source,
         directory / guide, directory / output, "--kind", "object", "--min-alpha", "32"],
        directory / "processing-logs" / f"{output}.json")
    return read(directory / output / "result.json")


def sprite_override(directory, sprite_id, role, source, guide, processing, elevation):
    entry = processing["sprites"][0]
    registration = copy.deepcopy(entry["registration"])
    registration.update(guide=guide, sourceImage=source, sourceSHA256=sha(directory / source),
                        reusedSourceRun=ORIGINAL_ID)
    return {"id": sprite_id, "role": role, "sourceImage": source,
            "sourceSHA256": sha(directory / source), "generationRecipe": f"generation-{1 if source == 'source-01.png' else 2:02}.json",
            "reusedSourceRun": ORIGINAL_ID, "elevationPx": elevation,
            "registration": registration, "normalization": entry["normalization"],
            "cleanup": processing["cleanup"], "panelIsolation": processing["panelIsolation"],
            "sourceProcessing": f"{'processed' if directory.name == 'lava-tile' else 'processed-' + ('01' if source == 'source-01.png' else '02')}/result.json"}


def assemble(case_id):
    directory = ROOT / case_id
    base = {"kind": "object" if case_id == "lava-tile" else "layered",
            "projection": "top-down-oblique-square-grid", "elevationPx": 32 if case_id == "lava-tile" else 160,
            "occupiedCells": [[0, 0]], "workflow": "3d-imagegen-reskin", "provenance": provenance(case_id),
            "independentReviewPending": True}
    if case_id == "lava-tile":
        guide = read(directory / "guide.json")
        geometry = read(directory / "authored-render/geometry-result.json")
        assert geometry["sprites"][0]["anchor"] == guide["anchor"] == [96, 248]
        assert geometry["sprites"][0]["elevationPx"] == guide["elevationPx"] == 32
        processing = extract(case_id, "source-01.png", "guide.json", "processed")
        base.update(declaredGeometry={key: guide[key] for key in ("frame", "anchor", "footprint", "occupiedCells", "elevationPx", "nominalHeightPx")},
                    cleanup=processing["cleanup"], panelIsolation=processing["panelIsolation"],
                    sprites=[sprite_override(directory, "lava-tile", "object", "source-01.png", "guide.json", processing, guide["elevationPx"])])
        inputs = ["processed/result.json"]
    else:
        geometry = read(directory / "geometry-reference/guide.json")
        assert geometry["anchor"] == [96, 248] and geometry["supportElevationPx"] == 48
        assert geometry["supportElevationBakedIntoArt"] is True
        assert geometry["attachmentPoint"] == [96, 220.48]
        stool = extract(case_id, "source-01.png", "guides/stool.json", "processed-01")
        character = extract(case_id, "source-02.png", "guides/character.json", "processed-02")
        base["declaredGeometry"] = {key: geometry[key] for key in (
            "frame", "anchor", "footprint", "occupiedCells", "supportElevationPx",
            "supportElevationBakedIntoArt", "attachmentWorld", "attachmentPoint")}
        base["declaredGeometry"].update(nominalStandingHeightPx=geometry["nominalHeightPx"],
                                       elevationOffsetAppliedDuringRecompositionPx=0)
        stool_override = sprite_override(directory, "stool", "stool", "source-01.png", "guides/stool.json", stool, 48)
        character_override = sprite_override(directory, "character", "character", "source-02.png", "guides/character.json", character, 160)
        stool_override.update(supportElevationPx=48, attachmentPoint=geometry["attachmentPoint"], drawOrder=0)
        character_override.update(supportElevationPx=48, supportElevationBakedIntoArt=True,
                                  attachmentPoint=geometry["attachmentPoint"], attachmentWorld=geometry["attachmentWorld"],
                                  elevationOffsetAppliedDuringRecompositionPx=0, drawOrder=1)
        base["sprites"] = [stool_override, character_override]
        base["recomposition"] = {"method": "alpha-composite complete independent canvases at stored common ground roots",
                                 "groundAnchor": [96, 248], "offsetsPx": [[0, 0], [0, 0]],
                                 "elevationOffsetAppliedPx": 0, "perArtFitting": False, "flattenedSceneSliced": False}
        inputs = ["processed-01/result.json", "processed-02/result.json"]
    write(directory / "registration.json", base)
    args = [SCRIPTS / "assemble_result.py"]
    for path in inputs:
        args += ["--input-result", directory / path]
    run([*args, "--registration", directory / "registration.json", "--output", directory / "result.json"],
        directory / "processing-logs/assembly.json")


def previews(case_id):
    directory = ROOT / case_id
    result = read(directory / "result.json")
    out = directory / "previews"
    out.mkdir()
    images = []
    records = []
    for sprite in result["sprites"]:
        image = Image.open(directory / sprite["image"]).convert("RGBA")
        images.append(image)
        records.append((sprite["id"], image))
    if len(images) > 1:
        recomposed = Image.new("RGBA", tuple(result["sprites"][0]["size"]))
        for image in images:
            recomposed.alpha_composite(image, (0, 0))
        recomposed.save(out / "recomposed.png")
        records.append(("recomposed", recomposed))
    files = []
    for name, image in records:
        for theme, color in (("light", "#eee9df"), ("dark", "#19212d")):
            canvas = Image.new("RGBA", image.size, color)
            canvas.alpha_composite(image)
            for label, scale in (("native", 1), ("2x", 2)):
                path = out / f"{name}-{theme}-{label}.png"
                canvas.convert("RGB").resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST).save(path)
                files.append(path.relative_to(directory).as_posix())
    write(out / "preview-recipe.json", {"script": "../../reprocess.py", "runtimeFrame": [192, 320],
          "source": [s["image"] for s in result["sprites"]], "placement": "worldGround - stored localAnchor",
          "commonGroundAnchor": [96, 248], "layerOffsetsPx": [[0, 0] for _ in images],
          "supportElevationBakedIntoArt": case_id == "seated-character-separated",
          "elevationOffsetAppliedPx": 0, "perArtFitting": False, "flattenedSceneSliced": False,
          "displayScales": {"native": 1, "2x": 2}, "displayResampling": "NEAREST",
          "files": files, "visualQualityCertified": False})
    return files


def finalize(case_id, files):
    directory = ROOT / case_id
    original_submission = read(ORIGINAL / case_id / "submission.json")
    submission = copy.deepcopy(original_submission)
    submission.pop("deliveryStatus", None)
    submission.update(outputDirectory=str(directory), userPrompt=(directory / "request.txt").read_text().rstrip("\n"),
                      reusedSourceRun=ORIGINAL_ID, thisProcessingRunImageGenerationCalls=0,
                      originalImageGenerationCalls=1 if case_id == "lava-tile" else 2,
                      deliveryStatus="processed-awaiting-independent-review")
    for source in submission["sources"]:
        if source.get("role") in ("stool", "character-only"):
            source["subjectRole"] = source.pop("role")
        source.update(reusedSourceRun=ORIGINAL_ID, thisProcessingRunImageGenerationCalls=0)
    write(directory / "submission.json", submission)
    write(directory / "execution.json", {"caseId": case_id, "workflow": "3d-imagegen-reskin",
          "processingMode": "processing-only-comparison", "status": "processed-awaiting-independent-review",
          "reusedSourceRun": ORIGINAL_ID, "originalImageGenerationCalls": 1 if case_id == "lava-tile" else 2,
          "thisProcessingRunImageGenerationCalls": 0, "actualGenerationCalls": 0,
          "processor": {"path": "../skill-snapshot/scripts/extract_registered_sheet.py",
                        "sha256": sha(SCRIPTS / "extract_registered_sheet.py"), "minAlpha": 32},
          "processingLogs": "processing-logs", "resultSHA256": sha(directory / "result.json"),
          "submissionSHA256": sha(directory / "submission.json"), "reviewPreviews": files,
          "independentReviewPending": True,
          "geometryDeclaration": "Authored roots/footprints remain declared constraints; corrected canvas rounding does not repair visual drift"})


def main():
    prepared = read(ROOT / "run.json")
    assert [trial["caseId"] for trial in prepared["trials"]] == list(CASES)
    for case_id in CASES:
        copy_evidence(case_id)
        assemble(case_id)
        finalize(case_id, previews(case_id))
    prepared.update(id=ROOT.name, label="Same AI reskin · corrected canvas rounding",
                    mode="processing-only-comparison", createdAt=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    originalRun=ORIGINAL_ID, actualGenerationCalls=0,
                    originalImageGenerationCalls=3, thisProcessingRunImageGenerationCalls=0,
                    provenance={"parentRun": ORIGINAL_ID, "sources": "Same three original generated PNGs; no new AI calls",
                                "change": "Compute common least-squares canvas scalar before testing each dimension's <=1 source-pixel residual",
                                "originalRunModified": False, "rubricModified": False})
    # Parent owns trial review/grade statuses. Keep the prepared statuses until
    # independent reviews are complete, while each case records processing.
    write(ROOT / "run.json", prepared)
    write(ROOT / "processing-command-log.json", {"imageGenerationCalls": 0, "commands": COMMANDS,
          "script": "reprocess.py", "scriptSHA256": sha(Path(__file__)),
          "copyOperation": "Byte-identical source/recipe/guide/reference/geometry files; SHA256 inventory in each provenance/reused-source.json",
          "previewOperation": "Composite independently extracted full canvases at identical stored roots; light/dark PNGs at native and nearest-neighbor 2x"})
    print(json.dumps({"run": str(ROOT), "cases": list(CASES), "actualGenerationCalls": 0}, indent=2))


if __name__ == "__main__":
    main()
