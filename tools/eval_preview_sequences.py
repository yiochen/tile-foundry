"""Expose preserved source sequences for viewing, without creating runtime sprites."""
import hashlib
import json
from tilekit import load_rgba


def partition_is_complete(rectangles, size):
    width, height = size
    area = 0
    for i, (left, top, right, bottom) in enumerate(rectangles):
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            return False
        area += (right-left)*(bottom-top)
        for x0,y0,x1,y1 in rectangles[:i]:
            if min(right,x1)>max(left,x0) and min(bottom,y1)>max(top,y0):
                return False
    return area == width*height


def transparent_cut(alpha, start, end, vertical):
    """Choose a transparent gutter; tolerate alpha-1 noise without deleting it."""
    bands = []
    for position in range(start,end):
        rect = ((position,0,position+1,alpha.height) if vertical
                else (0,position,alpha.width,position+1))
        if alpha.crop(rect).getextrema()[1] <= 1:
            if bands and bands[-1][1] == position:
                bands[-1][1] = position+1
            else:
                bands.append([position,position+1])
    if not bands:
        raise ValueError('No transparent gutter (alpha <= 1/255); source panels cannot be previewed independently')
    left,right = max(bands,key=lambda band:band[1]-band[0])
    return (left+right)//2


def source_sequence(directory, submission, guide, publish):
    """Return display-only frames; original result.json and its grading stay intact."""
    sources = submission['sources']
    source_path = directory/sources[0]['image']
    source = load_rgba(source_path)
    saved = directory/'previews/source-panels.json'
    if saved.is_file():
        records = json.loads(saved.read_text())
        if records.get('kind') != 'unprocessed-source-panels':
            raise ValueError('Unsupported source-panel record')
        frames = records['frames']
        if [f['index'] for f in frames] != list(range(len(frames))) or not partition_is_complete(
                [f['sourceRect'] for f in frames],source.size):
            raise ValueError('Saved source panels must partition the complete original sheet')
        measured = all(isinstance(f.get('floorObservation',{}).get('anchor'),list) for f in frames)
        published = []
        for frame in frames:
            path = directory/frame['sourcePreview']
            # Resolve through the publisher's containment check before reading.
            image_url = publish(path)
            image = load_rgba(path)
            if image.size != tuple(frame['actualSize']) or image.tobytes() != source.crop(frame['sourceRect']).tobytes():
                raise ValueError('Saved preview panel differs from its original source pixels')
            published.append({'id':f"source-{frame['index']}",'index':frame['index'],
                'image':image_url,'size':list(image.size),
                'anchor':frame['floorObservation']['anchor'] if measured else [0,0]})
        alignment = 'recorded-floor-center' if measured else 'panel-origin'
        note = ('Raw source panels at their recorded inferred floor centers; calibration floors remain. '
                'These are not normalized runtime sprites.' if measured else
                'Raw source panels at a fixed panel origin; no runtime registration is established.')
    elif guide.get('kind') in ('authored-material-animation-sheet','object-sheet','rendered-3d-sheet') and len(guide.get('cells',[]))>1:
        columns,rows = guide['columns'],guide['rows']
        cells = sorted(guide['cells'],key=lambda cell:cell['index'])
        if columns<1 or rows<1 or [c['index'] for c in cells] != list(range(columns*rows)):
            raise ValueError('Material sheet needs an explicit ordered grid')
        sx,sy = source.width/guide['size'][0],source.height/guide['size'][1]
        alpha = source.getchannel('A')
        xs = [0]+[transparent_cut(alpha,round(cells[c-1]['rect'][2]*sx),
                                  round(cells[c]['rect'][0]*sx),True) for c in range(1,columns)]+[source.width]
        ys = [0]+[transparent_cut(alpha,round(cells[(r-1)*columns]['rect'][3]*sy),
                                  round(cells[r*columns]['rect'][1]*sy),False) for r in range(1,rows)]+[source.height]
        image_url = publish(source_path)
        published = []
        rectangles = []
        for row in range(rows):
            for column in range(columns):
                rect = [xs[column],ys[row],xs[column+1],ys[row+1]]
                rectangles.append(rect)
                index = len(published)
                published.append({'id':f'source-{index}','index':index,'image':image_url,
                    'sourceRect':rect,'size':[rect[2]-rect[0],rect[3]-rect[1]],'anchor':[0,0]})
        if not partition_is_complete(rectangles,source.size):
            raise ValueError('Source preview must retain every original pixel')
        alignment = 'panel-origin'
        note = ('Raw source panels including their gutters and faint source noise, shown at a fixed panel origin. '
                'Calibration floors remain when present; these are not normalized runtime sprites.')
    elif len(sources)>1:
        published = []
        for index,record in enumerate(sources):
            image_url = publish(directory/record['image'])
            image = load_rgba(directory/record['image'])
            published.append({'id':f'source-{index}','index':index,'image':image_url,
                              'size':list(image.size),'anchor':[0,0]})
        alignment = 'panel-origin'
        note = 'Complete raw source assets at a fixed panel origin. Cycling layers is an inspection aid; common runtime registration has not been established.'
    else:
        return None
    sequence = {'kind':'unprocessed-source-sequence','fps':12,'alignment':alignment,
                'isProcessedSprite':False,'note':note,'frames':published,
                'sourceSHA256':{s['image']:hashlib.sha256((directory/s['image']).read_bytes()).hexdigest() for s in sources}}
    if guide.get('kind') in ('authored-material-animation-sheet','object-sheet','rendered-3d-sheet'):
        sequence['separatorAlphaMax'] = 1
    return sequence
