#!/usr/bin/env python3
"""Deterministic tile processing. Coordinates use top-left origin and pixel edges."""
from __future__ import annotations

import argparse
import colorsys
import json
import math
from statistics import median
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def load_rgba(path):
    with Image.open(path) as source:
        if "A" not in source.getbands() and "transparency" not in source.info:
            raise ValueError(f"{path}: no alpha channel; use transparent generation or an explicit mask")
        return source.convert("RGBA")


def alpha_bounds(image, threshold=8):
    if not 0 <= threshold <= 254:
        raise ValueError("Alpha threshold must be 0..254")
    bounds = image.getchannel("A").point(lambda a: 255 if a > threshold else 0).getbbox()
    if bounds is None:
        raise ValueError("Image is empty at the requested alpha threshold")
    return bounds


def clean_alpha(image, min_alpha=32):
    """Remove only weak alpha noise, without guessing an RGB background color."""
    if not 1 <= min_alpha <= 254:
        raise ValueError("min-alpha must be 1..254")
    output = image.copy()
    alpha = output.getchannel("A")
    histogram = alpha.histogram()
    output.putalpha(alpha.point(lambda a: a if a >= min_alpha else 0))
    alpha_bounds(output)
    return output, {"minAlpha": min_alpha, "removedPixels": sum(histogram[1:min_alpha]),
                    "warning": "Review at final size: intentionally faint details can also be removed."}


def crop_alpha(image, anchor=None, padding=0, threshold=8):
    """Crop the whole alpha silhouette; preserve ground anchor, including outside art."""
    if padding < 0:
        raise ValueError("Padding cannot be negative")
    box = alpha_bounds(image, threshold)
    if anchor is None:
        anchor = ((box[0] + box[2]) / 2, box[3])
    cropped = image.crop(box)
    output = Image.new("RGBA", (cropped.width + 2 * padding, cropped.height + 2 * padding))
    output.paste(cropped, (padding, padding))
    return output, {
        "sourceSize": list(image.size), "sourceRect": list(box),
        "anchor": [anchor[0] - box[0] + padding, anchor[1] - box[1] + padding],
        "anchorSource": list(anchor), "size": list(output.size),
    }


def split_grid(image, cell, columns, rows, margin=0, spacing=0):
    if min(*cell, columns, rows) <= 0 or min(margin, spacing) < 0:
        raise ValueError("Grid dimensions must be positive; margins and spacing nonnegative")
    needed = (2 * margin + columns * cell[0] + (columns - 1) * spacing,
              2 * margin + rows * cell[1] + (rows - 1) * spacing)
    if needed[0] > image.width or needed[1] > image.height:
        raise ValueError(f"Grid requires {needed}, source is {image.size}; refusing truncated cuts")
    tiles = []
    for row in range(rows):
        for col in range(columns):
            x = margin + col * (cell[0] + spacing)
            y = margin + row * (cell[1] + spacing)
            rect = (x, y, x + cell[0], y + cell[1])
            tiles.append((image.crop(rect), {"row": row, "column": col, "sourceRect": list(rect)}))
    return tiles


def component_rects(image, threshold=8, min_area=32, join_radius=0):
    """Flood-fill alpha. Optional dilation groups nearby detached sprite fragments."""
    if min_area < 1 or not 0 <= join_radius <= 32:
        raise ValueError("min-area must be positive; join-radius must be 0..32")
    mask = image.getchannel("A").point(lambda a: 255 if a > threshold else 0)
    if join_radius:
        mask = mask.filter(ImageFilter.MaxFilter(2 * join_radius + 1))
    pixels = bytearray(mask.tobytes())
    w, h = image.size
    results = []
    for start in range(w * h):
        if not pixels[start]:
            continue
        pixels[start] = 0
        queue = deque([start])
        x0 = x1 = start % w
        y0 = y1 = start // w
        count = 0
        while queue:
            index = queue.popleft()
            x, y = index % w, index // w
            x0, x1 = min(x0, x), max(x1, x)
            y0, y1 = min(y0, y), max(y1, y)
            count += 1
            # Eight-connected alpha handles antialiased diagonal silhouettes.
            for ny in range(max(0, y - 1), min(h, y + 2)):
                for nx in range(max(0, x - 1), min(w, x + 2)):
                    neighbor = ny * w + nx
                    if pixels[neighbor]:
                        pixels[neighbor] = 0
                        queue.append(neighbor)
        if count >= min_area:
            # Dilation is only for grouping; restore the true silhouette bounds.
            expanded = (x0, y0, x1 + 1, y1 + 1)
            original = image.crop(expanded)
            real = alpha_bounds(original, threshold)
            results.append((x0 + real[0], y0 + real[1], x0 + real[2], y0 + real[3]))
    return sorted(results, key=lambda b: (b[1], b[0]))


def normalize(image, frame=(192, 320), anchor_out=(96, 312), art_width=128,
              anchor_in=None, footprint=(128, 128), threshold=8, scale=None):
    cropped, info = crop_alpha(image, anchor_in, threshold=threshold)
    if min(*frame, *footprint, art_width) <= 0:
        raise ValueError("Frame, footprint, and art width must be positive")
    scale = scale if scale is not None else art_width / cropped.width
    if scale <= 0:
        raise ValueError("Scale must be positive")
    size = (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale)))
    # Store the actual per-axis scale introduced by rounding, preserving exact anchors.
    sx, sy = size[0] / cropped.width, size[1] / cropped.height
    scaled_anchor = (info["anchor"][0] * sx, info["anchor"][1] * sy)
    x, y = round(anchor_out[0] - scaled_anchor[0]), round(anchor_out[1] - scaled_anchor[1])
    if x < 0 or y < 0 or x + size[0] > frame[0] or y + size[1] > frame[1]:
        raise ValueError(f"Art at {(x, y, *size)} exceeds frame {frame}; enlarge the frame or choose an explicit scale")
    output = Image.new("RGBA", frame)
    output.paste(cropped.resize(size, Image.Resampling.LANCZOS), (x, y))
    # Fractional source anchors must converge to the same exact frame anchor.
    # Translate the composed frame by the residual after integer-pixel placement.
    shift = [anchor_out[0] - x - scaled_anchor[0], anchor_out[1] - y - scaled_anchor[1]]
    if any(abs(value) > 1e-9 for value in shift):
        output = output.transform(frame, Image.Transform.AFFINE,
                                  (1, 0, -shift[0], 0, 1, -shift[1]), Image.Resampling.BICUBIC)
    return output, {
        **info, "size": list(frame), "anchor": list(anchor_out), "subpixelShift": shift,
        "footprint": list(footprint), "artRect": [x, y, *size],
        "scale": [sx, sy], "sourceAnchorMode": "explicit" if anchor_in else "alpha-bottom-center",
    }


def floor_anchor(image, mode="solid", threshold=64):
    """Infer a calibration floor from alpha geometry, never from guessed colors.

    Solid guides require a wide connected screen-aligned floor band. Corner guides
    require four detached small components surrounding one character component.
    This returns observed geometry; it never forces a redraw into the SVG shape.
    """
    if not 1 <= threshold <= 254:
        raise ValueError("Alpha threshold must be 1..254")
    if mode == "corners":
        boxes = component_rects(image, threshold=threshold-1, min_area=max(8, image.width*image.height//20000))
        if len(boxes) != 5:
            raise ValueError(f"Expected one character and four detached corner marks; found {len(boxes)} components")
        character = max(boxes, key=lambda b:(b[2]-b[0])*(b[3]-b[1]))
        marks = [b for b in boxes if b != character]
        rect = (min(b[0] for b in marks), min(b[1] for b in marks), max(b[2] for b in marks), max(b[3] for b in marks))
        cx, cy = (rect[0]+rect[2])/2, (rect[1]+rect[3])/2
        quadrants = {(int((b[0]+b[2])/2 > cx), int((b[1]+b[3])/2 > cy)) for b in marks}
        if len(quadrants) != 4 or any((b[2]-b[0]) > (rect[2]-rect[0])*.25 or (b[3]-b[1]) > (rect[3]-rect[1])*.25 for b in marks):
            raise ValueError("Detached components do not form four small calibration corners")
        extra = {"characterRect":list(character),"markerRects":[list(b) for b in marks],"nominalSpan":132}
    elif mode == "solid":
        alpha = image.getchannel("A")
        data = alpha.tobytes()
        rows = []
        for y in range(image.height):
            runs=[]; start=None
            for x in range(image.width+1):
                opaque=x<image.width and data[y*image.width+x]>=threshold
                if opaque and start is None: start=x
                if not opaque and start is not None:
                    runs.append((start,x)); start=None
            rows.append(max(runs,key=lambda r:r[1]-r[0],default=(0,0)))
        maximum=max(r[1]-r[0] for r in rows)
        if maximum < 8:
            raise ValueError("No substantial opaque floor or character")
        bands=[]; start=None
        for y in range(image.height+1):
            broad=y<image.height and rows[y][1]-rows[y][0]>=maximum*.88
            if broad and start is None: start=y
            if not broad and start is not None:
                if y-start>=maximum*.3: bands.append((start,y))
                start=None
        if not bands:
            raise ValueError("No wide connected alpha band identifies the floor")
        top,bottom=bands[-1]
        # A hand can touch the floor's top edge and protrude into a few rows.
        # Use typical band edges so that protrusion does not set floor scale.
        rect=(round(median(r[0] for r in rows[top:bottom])),top,
              round(median(r[1] for r in rows[top:bottom])),bottom)
        extra={"nominalSpan":128,"detector":"Last wide contiguous alpha band with median side edges; inspect occlusion or perspective"}
    else:
        raise ValueError("Floor mode must be solid or corners")
    return {"mode":mode,"rect":list(rect),"anchor":[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2],
            "aspect":(rect[2]-rect[0])/(rect[3]-rect[1]),"alphaThreshold":threshold,**extra}


def remove_detached_markers(image, observation):
    """Keep a complete detached character; reject overlaps instead of cutting feet."""
    if observation.get("mode") != "corners":
        raise ValueError("Only detached corner guides can be removed by component isolation")
    box=tuple(observation["characterRect"])
    threshold=observation['alphaThreshold']
    alpha=image.getchannel('A').tobytes();w,h=image.size
    seed=next((y*w+x for y in range(box[1],box[3]) for x in range(box[0],box[2]) if alpha[y*w+x]>=threshold),None)
    if seed is None: raise ValueError("Character component is empty")
    kept={seed};queue=deque([seed])
    while queue:
        index=queue.popleft();x,y=index%w,index//w
        for ny in range(max(0,y-1),min(h,y+2)):
            for nx in range(max(0,x-1),min(w,x+2)):
                neighbor=ny*w+nx
                if neighbor not in kept and alpha[neighbor]>=threshold:
                    kept.add(neighbor);queue.append(neighbor)
    # Bounds may overlap even when the actual silhouettes are detached. Keep the
    # connected pixel set rather than a rectangular crop that could retain marks.
    pixels=list(image.getdata())
    output=Image.new('RGBA',image.size)
    output.putdata([p if i in kept else (0,0,0,0) for i,p in enumerate(pixels)])
    return output,{"method":"Detached alpha-component isolation; full frame and floor-derived anchor retained", "characterRect":list(box),"exactKeptPixels":True,"keptPixels":len(kept)}


def subtract_authored_floor(image, floor):
    """Diagnostic exact-pixel subtraction of a known registered floor, not chroma key.

    Pixels different from the authored reference are retained. A redrawn or shaded
    floor therefore remains visible. This cannot unmix antialiased character edges
    that were composited into an opaque floor; it is not a production matte.
    """
    if image.size != floor.size:
        raise ValueError("Image and registered floor must share a frame")
    current=list(image.getdata()); reference=list(floor.getdata()); removed=0
    for i,(p,q) in enumerate(zip(current,reference)):
        if q[3] and p==q:
            current[i]=(p[0],p[1],p[2],0); removed+=1
    output=Image.new("RGBA",image.size);output.putdata(current)
    probes=[i for i,q in enumerate(reference) if q[3]>=250 and (i%image.width<48 or i%image.width>=144)]
    residual=sum(current[i][3]>=64 for i in probes)
    return output,{"method":"Exact RGBA subtraction against the authored floor; diagnostic only", "removedPixels":removed,
                   "floorMarginResidualPixels":residual,"floorMarginProbePixels":len(probes),
                   "floorMarginResidualFraction":residual/len(probes) if probes else None,
                   "productionSafe":False,"limitation":"Redrawn floor pixels and opaque character/floor mixtures cannot be separated exactly"}


def remove_floor_chroma(image, observation, key_rgb, hue_tolerance=28, hue_feather=8,
                        min_saturation=.12, saturation_feather=.10, remove_corner_remnants=False):
    """Explicit, approximate chroma key inside an already measured floor rectangle.

    The caller supplies the reserved key color; no background color is inferred.
    Geometry must be measured before keying. Frame and stored anchor do not move.
    Soft keying cannot recover an exact matte from opaque composited boot edges.
    """
    if observation.get('mode') != 'solid':
        raise ValueError('Chroma floor removal requires a measured solid floor')
    if len(key_rgb) != 3 or any(not 0 <= c <= 255 for c in key_rgb):
        raise ValueError('Key RGB must have three values in 0..255')
    kh,ks,_=colorsys.rgb_to_hsv(*(c/255 for c in key_rgb))
    if ks < .1:
        raise ValueError('Key color must have a defined saturated hue')
    if not 0 < hue_tolerance < 180 or not 0 < hue_feather <= 90:
        raise ValueError('Hue tolerance/feather must be positive degrees')
    if not 0 < saturation_feather <= min_saturation <= 1:
        raise ValueError('Require 0 < saturation feather <= minimum saturation <= 1')
    rect=observation['rect']
    left,top,right,bottom=rect
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ValueError('Measured floor must fit the full image frame')
    # Three pixels include the Lanczos fringe after floor-derived normalization.
    region=(max(0,math.floor(left)-3),max(0,math.floor(top)-3),
            min(image.width,math.ceil(right)+3),min(image.height,math.ceil(bottom)+3))
    output=image.copy();src=image.load();dst=output.load()
    keyed=cleared=0;removed_alpha=0
    for y in range(region[1],region[3]):
        for x in range(region[0],region[2]):
            r,g,b,a=src[x,y]
            if not a: continue
            h,s,_=colorsys.rgb_to_hsv(r/255,g/255,b/255)
            distance=abs(h-kh)*360;distance=min(distance,360-distance)
            hue_weight=max(0,min(1,(hue_tolerance+hue_feather-distance)/hue_feather))
            sat_weight=max(0,min(1,(s-min_saturation+saturation_feather)/saturation_feather))
            weight=hue_weight*sat_weight
            alpha=round(a*(1-weight))
            if alpha < a:
                keyed+=1;cleared+=int(alpha==0);removed_alpha+=a-alpha
                dst[x,y]=(r,g,b,alpha) if alpha else (0,0,0,0)
    remnants=[]
    if remove_corner_remnants:
        # Authored cream L accents can become white and survive a green hue key.
        # Remove only detached, pale components wholly in a known corner region.
        span=min(right-left,bottom-top);reach=span*.18
        corners=[(cx-reach,cy-reach,cx+reach,cy+reach)
                 for cx in (left,right) for cy in (top,bottom)]
        for box in component_rects(output,threshold=0,min_area=1):
            if not any(box[0]>=c[0] and box[1]>=c[1] and box[2]<=c[2] and box[3]<=c[3] for c in corners):
                continue
            visible=[p for p in output.crop(box).getdata() if p[3]]
            if visible and all(colorsys.rgb_to_hsv(*(c/255 for c in p[:3]))[1] <= .3 for p in visible):
                output.paste((0,0,0,0),box);remnants.append(list(box))
    return output,{'method':'Explicit floor-region chroma key with a soft hue/saturation matte',
        'keyRGB':list(key_rgb),'keyHueDegrees':round(kh*360,2),'hueToleranceDegrees':hue_tolerance,
        'hueFeatherDegrees':hue_feather,'minSaturation':min_saturation,
        'saturationFeather':saturation_feather,'region':list(region),'regionPaddingPixels':3,
        'keyedPixels':keyed,'clearedPixels':cleared,'removedAlphaMass':removed_alpha,
        'removedCornerRemnants':remnants,'size':list(image.size),'anchor':observation['anchor'],
        'exactCharacterMatte':False,'limitation':'Reserve the key hue in the floor region; mixed shoe edges are approximate and green character parts there would also be keyed'}


def composite_reference(floor, character, scale=4):
    """Composite known separate layers for an AI guide; keep their complete frame."""
    if floor.size != character.size or scale < 1:
        raise ValueError("Guide layers must share a frame and scale must be positive")
    output=floor.copy()
    output.alpha_composite(character)
    return output,output.resize((output.width*scale,output.height*scale),Image.Resampling.LANCZOS)


def prepare_floor_material(image, cell_size=128):
    """Uniformly resample a complete square ground material; never crop or fill holes."""
    if cell_size<1 or image.width!=image.height:
        raise ValueError('Ground material must be a complete square; no axis stretching or cropping')
    if image.getchannel('A').getextrema()[0]<250:
        raise ValueError('Ground material has transparent gaps; regenerate a full opaque square')
    result=image.resize((cell_size,cell_size),Image.Resampling.LANCZOS)
    return result,{'version':1,'kind':'floor','size':[cell_size,cell_size],
        'anchor':[cell_size/2,cell_size/2],'footprint':[cell_size,cell_size],
        'sourceSize':list(image.size),'scale':cell_size/image.width,
        'method':'Whole square material, uniform resampling; no crop or guessed-color removal'}


def process_floor_object(image,key_rgb,frame=(192,320),anchor=(96,248),cell_size=128,min_alpha=32):
    """Calibrate the intact floor, then key it without fitting the character's feet."""
    cleaned,cleanup=clean_alpha(image,min_alpha)
    floor=floor_anchor(cleaned)
    if not .95<=floor['aspect']<=1.05:
        raise ValueError('Calibration floor is not square enough; regenerate instead of warping')
    scale=cell_size/(floor['rect'][2]-floor['rect'][0])
    intact,normalization=normalize(cleaned,frame=frame,anchor_out=anchor,
        anchor_in=floor['anchor'],scale=scale,footprint=(cell_size,cell_size))
    registered={**floor_anchor(intact),'anchor':list(anchor)}
    cutout,chroma=remove_floor_chroma(intact,registered,key_rgb)
    return cutout,{'size':list(frame),'anchor':list(anchor),'footprint':[cell_size,cell_size],
        'floor':floor,'cleanup':cleanup,'normalization':normalization,'chroma':chroma,
        'anchorMode':'Measured calibration-floor center, independent of feet or cutout bounds'}


def process_object_sheet(image,guide,min_alpha=32,allow_gutter_drift=False):
    """Split only known isolated guide panels; reject opaque art in their gutters."""
    if guide.get('kind')!='object-sheet' or guide.get('version')!=1:
        raise ValueError('Expected version 1 object-sheet guide JSON')
    sx,sy=image.width/guide['size'][0],image.height/guide['size'][1]
    if abs(sx/sy-1)>.01:
        raise ValueError('Generated canvas aspect differs from guide; refusing distorted panel cuts')
    cleaned,cleanup=clean_alpha(image,min_alpha)
    rectangles=[tuple(round(c['rect'][i]*(sx if i%2==0 else sy)) for i in range(4)) for c in guide['cells']]
    alpha=cleaned.getchannel('A').tobytes()
    if allow_gutter_drift:
        if len(rectangles)!=guide['columns']*guide['rows']:
            raise ValueError('Alpha-seam recovery requires a complete rectangular panel grid')
        def clear_separator(start,end,vertical):
            clear=[]
            for value in range(start,end):
                occupied=any(alpha[y*image.width+value] for y in range(image.height)) if vertical else any(alpha[value*image.width:(value+1)*image.width])
                clear.append(not occupied)
            bands=[];first=None
            for i in range(len(clear)+1):
                if i<len(clear) and clear[i] and first is None:first=i
                if (i==len(clear) or not clear[i]) and first is not None:
                    bands.append((start+first,start+i));first=None
            if not bands:raise ValueError('No completely transparent separator in the guide gutter; generate isolated poses')
            left,right=max(bands,key=lambda b:b[1]-b[0])
            return (left+right)//2
        xs=[0]+[clear_separator(rectangles[c-1][2],rectangles[c][0],True)
                for c in range(1,guide['columns'])]+[image.width]
        ys=[0]+[clear_separator(rectangles[(r-1)*guide['columns']][3],rectangles[r*guide['columns']][1],False)
                for r in range(1,guide['rows'])]+[image.height]
        rectangles=[(xs[c],ys[r],xs[c+1],ys[r+1]) for r in range(guide['rows']) for c in range(guide['columns'])]
    # Validate guide geometry, and ensure crops contain all nonzero cleaned art.
    covered=bytearray(image.width*image.height)
    for left,top,right,bottom in rectangles:
        if not (0<=left<right<=image.width and 0<=top<bottom<=image.height):
            raise ValueError('Guide panel exceeds source canvas')
        for y in range(top,bottom):
            start=y*image.width+left;end=y*image.width+right
            if any(covered[start:end]):raise ValueError('Guide panels overlap')
            covered[start:end]=b'\x01'*(right-left)
    if any(a and not inside for a,inside in zip(alpha,covered)):
        raise ValueError('Art crosses a sheet gutter; regenerate isolated panels instead of clipping')
    frames=[]
    for i,rect in enumerate(rectangles):
        cutout,info=process_floor_object(cleaned.crop(rect),guide['keyRGB'],
            tuple(guide['frame']),tuple(guide['anchor']),guide['cellSize'],min_alpha)
        info.update({'index':i,'sourceRect':list(rect),'sheetCleanup':cleanup,
            'panelIsolation':'transparent-separators' if allow_gutter_drift else 'strict-guide-panels'})
        frames.append((cutout,info))
    return frames


def render_floor_repeat(image,repeats=3):
    output=Image.new('RGBA',(image.width*repeats,image.height*repeats))
    for y in range(repeats):
        for x in range(repeats):output.paste(image,(x*image.width,y*image.height))
    return output


def render_anchored_frames(frames,anchor=(96,248),dark=False):
    """Review each full frame at one world point, never at the visible foot bottom."""
    views=[]
    for image in frames:
        view=Image.new('RGBA',(256,384),'#18222e' if dark else '#f4f6ef')
        draw=ImageDraw.Draw(view)
        draw.rectangle((64,200,191,327),fill='#283543' if dark else '#dfe5dc',outline='#6b7f70')
        view.alpha_composite(image,(128-anchor[0],264-anchor[1]))
        draw.line((120,264,136,264),fill='#b72e74',width=1)
        draw.line((128,256,128,272),fill='#b72e74',width=1)
        views.append(view)
    strip=Image.new('RGBA',(256*len(views),384))
    for i,view in enumerate(views):strip.paste(view,(i*256,0))
    return views,strip


def pack_atlas(items, columns=4, padding=4, extrusion=2, trim=True):
    """Pack shelf cells; trimmed frame anchors are expressed in frame-local pixels."""
    if not items or columns < 1 or extrusion < 0 or padding < extrusion:
        raise ValueError("Require tiles, columns > 0, and padding >= extrusion >= 0")
    prepared = []
    for name, image, meta in items:
        box = alpha_bounds(image, 0) if trim else (0, 0, image.width, image.height)
        prepared.append((name, image.crop(box), meta, box))
    columns = min(columns, len(items))
    cell_w = max(i.width for _, i, _, _ in prepared) + 2 * padding
    cell_h = max(i.height for _, i, _, _ in prepared) + 2 * padding
    atlas = Image.new("RGBA", (columns * cell_w, math.ceil(len(items) / columns) * cell_h))
    frames = {}
    for index, (name, tile, meta, box) in enumerate(prepared):
        x, y = (index % columns) * cell_w + padding, (index // columns) * cell_h + padding
        if extrusion:
            e = extrusion
            # Clamp edge texels into the surrounding gutter, including four corners.
            expanded = Image.new("RGBA", (tile.width + 2 * e, tile.height + 2 * e))
            expanded.paste(tile, (e, e))
            expanded.paste(tile.crop((0, 0, 1, tile.height)).resize((e, tile.height)), (0, e))
            expanded.paste(tile.crop((tile.width - 1, 0, tile.width, tile.height)).resize((e, tile.height)), (e + tile.width, e))
            expanded.paste(tile.crop((0, 0, tile.width, 1)).resize((tile.width, e)), (e, 0))
            expanded.paste(tile.crop((0, tile.height - 1, tile.width, tile.height)).resize((tile.width, e)), (e, e + tile.height))
            for xx, yy, tx, ty in [(0, 0, 0, 0), (e + tile.width, 0, tile.width - 1, 0),
                                   (0, e + tile.height, 0, tile.height - 1),
                                   (e + tile.width, e + tile.height, tile.width - 1, tile.height - 1)]:
                expanded.paste(Image.new("RGBA", (e, e), tile.getpixel((tx, ty))), (xx, yy))
            atlas.paste(expanded, (x - e, y - e))
        else:
            atlas.paste(tile, (x, y))
        frames[name] = {
            "frame": {"x": x, "y": y, "w": tile.width, "h": tile.height},
            "sourceSize": {"w": image.width, "h": image.height},
            "spriteSourceSize": {"x": box[0], "y": box[1], "w": tile.width, "h": tile.height},
            "anchor": [meta["anchor"][0] - box[0], meta["anchor"][1] - box[1]],
            "footprint": meta.get("footprint", [128, 128]),
        }
    return atlas, {"frames": frames, "meta": {"size": {"w": atlas.width, "h": atlas.height},
                  "padding": padding, "extrusion": extrusion, "trimmed": trim}}


def generate_guides(directory, frame=(192, 320), footprint=(128, 128), heights=(32, 64, 96)):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    ax, ay = frame[0] / 2, frame[1] - 8
    x0, x1 = ax - footprint[0] / 2, ax + footprint[0] / 2
    for height in heights:
        if ay - footprint[1] - height < 0:
            raise ValueError("Guide exceeds frame")
        guide = Image.new("RGBA", frame)
        draw = ImageDraw.Draw(guide)
        draw.rectangle((x0, ay - footprint[1] - height, x1 - 1, ay - height - 1), fill="#f1c879", outline="#9e7337", width=2)
        draw.rectangle((x0, ay - height, x1 - 1, ay - 1), fill="#b1803b", outline="#79562c", width=2)
        # Guides deliberately include lines; final art must not include these marks.
        draw.rectangle((x0, ay - footprint[1], x1 - 1, ay - 1), outline="#2b70da", width=1)
        draw.line((ax - 5, ay, ax + 5, ay), fill="#da4055", width=2)
        draw.line((ax, ay - 5, ax, ay + 5), fill="#da4055", width=2)
        guide.save(directory / f"height-{height}.png")
    write_json(directory / "guides.json", {"frame": frame, "footprint": footprint,
               "anchor": [ax, ay], "heights": list(heights), "projection": "orthogonal top and front; height extends upward"})


def neighbor_coverage(image, anchor, pitch=(128, 128), min_alpha=250, min_coverage=1.0):
    """Test a solid-cell sprite against neighbors; free silhouettes must opt out."""
    if min(*pitch) <= 0 or not 1 <= min_alpha <= 255 or not 0 < min_coverage <= 1:
        raise ValueError("Require positive pitch, alpha 1..255, and coverage 0..1")
    if any(int(v) != v for v in anchor):
        raise ValueError("Coverage check requires an integer normalized anchor")
    px, py = pitch
    pad_x, pad_y = image.width, image.height
    preview = Image.new("RGBA", (3 * px + 2 * pad_x, 3 * py + 2 * pad_y))
    for row in range(3):
        for col in range(3):
            x = round(pad_x + (col + .5) * px - anchor[0])
            y = round(pad_y + (row + 1) * py - anchor[1])
            preview.alpha_composite(image, (x, y))
    box = (pad_x + px, pad_y + py, pad_x + 2 * px, pad_y + 2 * py)
    alpha = preview.crop(box).getchannel("A")
    values = list(alpha.tobytes())
    missing = sum(a < min_alpha for a in values)
    coverage = 1 - missing / len(values)
    empty_rows = [y for y in range(py) if all(a < min_alpha for a in values[y * px:(y + 1) * px])]
    report = {"ok": coverage >= min_coverage, "coveredFraction": coverage,
              "uncoveredPixels": missing, "testedPixels": len(values), "emptyRows": empty_rows,
              "pitch": list(pitch), "alphaThreshold": min_alpha, "requiredCoverage": min_coverage,
              "scope": "Repeated identical solid cells; not material/color continuity or mixed-height joins."}
    return report, preview.crop(preview.getbbox())


def parallel_edges(image, body_rect=None, min_alpha=250, tolerance=1.0):
    """Compare opaque side spans in far/near body bands, excluding rounded corners."""
    if tolerance < 0 or not 1 <= min_alpha <= 255:
        raise ValueError("Require nonnegative tolerance and alpha 1..255")
    box = tuple(body_rect) if body_rect is not None else alpha_bounds(image, min_alpha - 1)
    x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 > image.width or y1 > image.height or x1 <= x0 or y1 <= y0:
        raise ValueError("Body rectangle must fit inside the image")
    alpha = image.getchannel("A")
    def band(fraction):
        center = round(y0 + (y1 - y0 - 1) * fraction)
        spans = []
        for y in range(max(y0, center - 2), min(y1, center + 3)):
            row = alpha.crop((x0, y, x1, y + 1)).point(lambda a: 255 if a >= min_alpha else 0).getbbox()
            if row is None:
                raise ValueError("No opaque body pixels in the selected band")
            spans.append((x0 + row[0], x0 + row[2]))
        return [median(s[0] for s in spans), median(s[1] for s in spans)]
    far, near = band(.2), band(.8)
    far_width, near_width = far[1] - far[0], near[1] - near[0]
    shift = max(abs(near[0] - far[0]), abs(near[1] - far[1]))
    return {"ok": abs(near_width - far_width) <= tolerance and shift <= tolerance,
            "farWidth": far_width, "nearWidth": near_width, "widthDelta": near_width - far_width,
            "sideShift": shift, "tolerance": tolerance, "bodyRect": list(box), "alphaThreshold": min_alpha,
            "scope": "Opaque silhouette bands only; inspect stud size, internal geometry, and shading visually."}


def validate_assets(assets, root):
    errors, warnings = [], []
    solid_checks = {}
    for asset in assets["tiles"]:
        image = load_rgba(Path(root) / asset["image"])
        ax, ay = asset["anchor"]
        if not 0 <= ax <= image.width or not 0 <= ay <= image.height:
            errors.append(f"{asset['id']}: anchor outside canvas")
        bbox = alpha_bounds(image)
        if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == image.width or bbox[3] == image.height:
            warnings.append(f"{asset['id']}: silhouette touches frame edge; inspect for clipping")
        if asset.get("sourceAnchorMode") == "alpha-bottom-center" and not asset.get("anchorReviewed"):
            warnings.append(f"{asset['id']}: automatic anchor; visually verify ground contact")
        if asset.get("solidCell"):
            options = asset["solidCell"]
            coverage, _ = neighbor_coverage(image, asset["anchor"], tuple(asset["footprint"]),
                                            options.get("minAlpha", 250), options.get("minCoverage", 1.0))
            parallel = parallel_edges(image, options.get("bodyRect"), min_alpha=options.get("minAlpha", 250),
                                      tolerance=options.get("edgeTolerance", 1.0))
            solid_checks[asset["id"]] = {"coverage": coverage, "parallel": parallel}
            if not coverage["ok"]:
                errors.append(f"{asset['id']}: repeated cells leave {coverage['uncoveredPixels']} uncovered pixels")
            if not parallel["ok"]:
                errors.append(f"{asset['id']}: near/far body edges taper or shift")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "solidChecks": solid_checks}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    def image_args(name):
        command = sub.add_parser(name)
        command.add_argument("input", type=Path)
        command.add_argument("output", type=Path)
        return command
    crop = image_args("crop-alpha")
    crop.add_argument("--padding", type=int, default=4)
    crop.add_argument("--anchor", type=float, nargs=2)
    crop.add_argument("--threshold", type=int, default=8)
    clean = image_args("clean-alpha")
    clean.add_argument("--min-alpha", type=int, default=32)
    grid = image_args("split-grid")
    grid.add_argument("--cell", type=int, nargs=2, required=True)
    grid.add_argument("--columns", type=int, required=True)
    grid.add_argument("--rows", type=int, required=True)
    grid.add_argument("--margin", type=int, default=0)
    grid.add_argument("--spacing", type=int, default=0)
    components = image_args("split-components")
    components.add_argument("--min-area", type=int, default=32)
    components.add_argument("--join-radius", type=int, default=0)
    components.add_argument("--threshold", type=int, default=8)
    norm = image_args("normalize")
    norm.add_argument("--frame", type=int, nargs=2, default=[192, 320])
    norm.add_argument("--anchor-out", type=float, nargs=2, default=[96, 312])
    norm.add_argument("--anchor-in", type=float, nargs=2)
    norm.add_argument("--art-width", type=int, default=128)
    norm.add_argument("--footprint", type=int, nargs=2, default=[128, 128])
    norm.add_argument("--scale", type=float)
    norm.add_argument("--threshold", type=int, default=8)
    guides = sub.add_parser("guides")
    guides.add_argument("output", type=Path)
    atlas = sub.add_parser("pack")
    atlas.add_argument("manifest", type=Path)
    atlas.add_argument("output", type=Path)
    atlas.add_argument("--columns", type=int, default=4)
    atlas.add_argument("--padding", type=int, default=4)
    atlas.add_argument("--extrusion", type=int, default=2)
    atlas.add_argument("--no-trim", action="store_true")
    check = sub.add_parser("validate")
    check.add_argument("manifest", type=Path)
    coverage = sub.add_parser("check-solid")
    coverage.add_argument("input", type=Path)
    coverage.add_argument("output", type=Path, help="JSON report; optional PNG proof saved alongside")
    coverage.add_argument("--anchor", type=int, nargs=2, required=True)
    coverage.add_argument("--pitch", type=int, nargs=2, default=[128, 128])
    coverage.add_argument("--min-alpha", type=int, default=250)
    coverage.add_argument("--min-coverage", type=float, default=1.0)
    coverage.add_argument("--body-rect", type=int, nargs=4, help="left top right bottom, excluding protruding art")
    coverage.add_argument("--edge-tolerance", type=float, default=1.0)
    coverage.add_argument("--preview", action="store_true")
    floor = sub.add_parser("floor-anchor", help="Infer a calibration cell center from alpha geometry")
    floor.add_argument("input", type=Path)
    floor.add_argument("output", type=Path)
    floor.add_argument("--mode", choices=("solid","corners"), default="solid")
    floor.add_argument("--min-alpha", type=int, default=64)
    subtract = sub.add_parser("subtract-floor", help="Diagnostic exact-pixel subtraction against an authored registered floor")
    subtract.add_argument("input", type=Path)
    subtract.add_argument("floor", type=Path)
    subtract.add_argument("output", type=Path)
    isolate = sub.add_parser("isolate-marked", help="Remove four detached calibration corners and retain the character frame")
    isolate.add_argument("input", type=Path)
    isolate.add_argument("output", type=Path)
    isolate.add_argument("--min-alpha", type=int, default=64)
    chroma = sub.add_parser("key-floor", help="Explicit color key inside a measured floor; retains its anchor and full frame")
    chroma.add_argument("input",type=Path)
    chroma.add_argument("output",type=Path)
    chroma.add_argument("--key-rgb",type=int,nargs=3,required=True)
    chroma.add_argument("--hue-tolerance",type=float,default=28)
    chroma.add_argument("--hue-feather",type=float,default=8)
    chroma.add_argument("--min-saturation",type=float,default=.12)
    chroma.add_argument("--saturation-feather",type=float,default=.10)
    chroma.add_argument("--remove-corner-remnants",action="store_true")
    chroma.add_argument("--min-alpha",type=int,default=64)
    ground=image_args('floor-material')
    ground.add_argument('--cell-size',type=int,default=128)
    sheet=sub.add_parser('process-on-floor',help='Normalize isolated guide panels from their floors, then chroma-key them')
    sheet.add_argument('input',type=Path)
    sheet.add_argument('guide',type=Path,help='Layout JSON from guide_tools.py')
    sheet.add_argument('output',type=Path,help='Directory for frames, spritesheet, and result.json')
    sheet.add_argument('--min-alpha',type=int,default=32)
    sheet.add_argument('--fps',type=float,default=12)
    sheet.add_argument('--allow-gutter-drift',action='store_true',help='Recover only across wholly transparent separators; preserves all cleaned source alpha')
    args = parser.parse_args()
    try:
        if args.command == "floor-anchor":
            write_json(args.output,floor_anchor(load_rgba(args.input),args.mode,args.min_alpha))
        elif args.command == 'floor-material':
            with Image.open(args.input) as source: image=source.convert('RGBA')
            result,info=prepare_floor_material(image,args.cell_size)
            args.output.parent.mkdir(parents=True,exist_ok=True);result.save(args.output)
            write_json(args.output.with_suffix('.json'),{**info,'image':args.output.name})
        elif args.command == 'process-on-floor':
            if args.fps<=0:raise ValueError('FPS must be positive')
            guide=json.loads(args.guide.read_text())
            frames=process_object_sheet(load_rgba(args.input),guide,args.min_alpha,args.allow_gutter_drift)
            directory=args.output;directory.mkdir(parents=True,exist_ok=True)
            (directory/'frames').mkdir(exist_ok=True)
            columns=guide['columns'];rows=guide['rows'];fw,fh=guide['frame']
            sheet_image=Image.new('RGBA',(columns*fw,rows*fh));entries=[]
            for i,(result,info) in enumerate(frames):
                name=f'frames/frame-{i:02}.png';result.save(directory/name)
                sheet_image.paste(result,((i%columns)*fw,(i//columns)*fh))
                entries.append({'id':f'frame-{i:02}','image':name,'durationMs':1000/args.fps,**info})
            sheet_image.save(directory/'sheet.png')
            write_json(directory/'result.json',{'version':1,'kind':'animation' if len(frames)>1 else 'object',
                'cellSize':guide['cellSize'],'groundAnchorAlignment':'center','frames':entries,
                'panelIsolation':'transparent-separators' if args.allow_gutter_drift else 'strict-guide-panels',
                'sheet':{'image':'sheet.png','columns':columns,'rows':rows,'frame':[fw,fh],'spacing':0},
                'guideLayout':guide,'sourceSize':list(load_rgba(args.input).size)})
        elif args.command == "key-floor":
            image,cleanup=clean_alpha(load_rgba(args.input),args.min_alpha)
            observation=floor_anchor(image,threshold=args.min_alpha)
            result,info=remove_floor_chroma(image,observation,args.key_rgb,args.hue_tolerance,
                args.hue_feather,args.min_saturation,args.saturation_feather,args.remove_corner_remnants)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            result.save(args.output)
            write_json(args.output.with_suffix('.json'),{**info,'floor':observation,'cleanup':cleanup})
        elif args.command in {"subtract-floor","isolate-marked"}:
            image=load_rgba(args.input)
            if args.command == "subtract-floor":
                result,info=subtract_authored_floor(image,load_rgba(args.floor))
            else:
                image,cleanup=clean_alpha(image,args.min_alpha)
                observation=floor_anchor(image,"corners",args.min_alpha)
                result,info=remove_detached_markers(image,observation)
                info.update({"floor":observation,"cleanup":cleanup,"anchor":observation['anchor'],"size":list(image.size)})
            args.output.parent.mkdir(parents=True,exist_ok=True)
            result.save(args.output)
            write_json(args.output.with_suffix(".json"),info)
        elif args.command == "guides":
            generate_guides(args.output)
        elif args.command in {"crop-alpha", "normalize", "clean-alpha"}:
            image = load_rgba(args.input)
            if args.command == "clean-alpha":
                result, info = clean_alpha(image, args.min_alpha)
            elif args.command == "crop-alpha":
                result, info = crop_alpha(image, args.anchor, args.padding, args.threshold)
            else:
                result, info = normalize(image, tuple(args.frame), tuple(args.anchor_out), args.art_width,
                                         args.anchor_in, tuple(args.footprint), threshold=args.threshold, scale=args.scale)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            result.save(args.output)
            write_json(args.output.with_suffix(".json"), info)
        elif args.command in {"split-grid", "split-components"}:
            image = load_rgba(args.input)
            args.output.mkdir(parents=True, exist_ok=True)
            if args.command == "split-grid":
                parts = split_grid(image, tuple(args.cell), args.columns, args.rows, args.margin, args.spacing)
            else:
                parts = [(image.crop(box), {"sourceRect": list(box)}) for box in
                         component_rects(image, args.threshold, args.min_area, args.join_radius)]
                if not parts:
                    raise ValueError("No nonempty components; review min-area/threshold")
            cuts = []
            for index, (part, meta) in enumerate(parts):
                filename = f"tile-{index:03}.png"
                part.save(args.output / filename)
                cuts.append({"image": filename, **meta})
            write_json(args.output / "cuts.json", {"source": str(args.input), "tiles": cuts})
        elif args.command == "pack":
            assets = json.loads(args.manifest.read_text())
            items = [(t["id"], load_rgba(args.manifest.parent / t["image"]), t) for t in assets["tiles"]]
            result, info = pack_atlas(items, args.columns, args.padding, args.extrusion, not args.no_trim)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            result.save(args.output)
            info["meta"]["image"] = args.output.name
            write_json(args.output.with_suffix(".json"), info)
        elif args.command == "check-solid":
            image = load_rgba(args.input)
            report, preview = neighbor_coverage(image, args.anchor, tuple(args.pitch), args.min_alpha, args.min_coverage)
            parallel = parallel_edges(image, args.body_rect, args.min_alpha, args.edge_tolerance)
            value = {"ok": report["ok"] and parallel["ok"], "coverage": report, "parallel": parallel}
            write_json(args.output, value)
            if args.preview:
                background = Image.new("RGBA", preview.size, "#ff33cc")
                background.alpha_composite(preview)
                background.convert("RGB").save(args.output.with_suffix(".png"))
            print(json.dumps(value, indent=2))
            if not value["ok"]:
                raise SystemExit(1)
        elif args.command == "validate":
            report = validate_assets(json.loads(args.manifest.read_text()), args.manifest.parent)
            print(json.dumps(report, indent=2))
            if not report["ok"]:
                raise SystemExit(1)
        print(f"{args.command}: complete")
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
