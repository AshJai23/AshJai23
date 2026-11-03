"""Build source-derived silver references BEFORE retrieval/model execution or tuning.

AI-authored questions and lexical labels are not independent human relevance gold.
The original 40-task contract is never modified by this script.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import duckdb

TOPICS=[
 ('photo_frame',['photo','frame'],'Find items for displaying photographs.'),
 ('cushion',['cushion'],'Find products for padding a sofa.'),
 ('doormat',['door.?mat'],'Find items for wiping muddy shoes at a doorway.'),
 ('fairy_lights',['fairy','light'],'Find products for small decorative strings of lights.'),
 ('tea_towel',['tea','towel'],'Find items used to dry dishes in a kitchen.'),
 ('wrapping_paper',['wrapp','paper'],'Find products for wrapping presents in patterned paper.'),
 ('necklace',['necklace'],'Find items worn around the neck as jewellery.'),
 ('bracelet',['bracelet'],'Find jewellery items for a wrist.'),
 ('earring',['earring'],'Find jewellery products worn on ears.'),
 ('ring',[r'\bring\b|\brings\b'],'Find jewellery products worn on fingers.'),
 ('scarf',['scarf|scarves'],'Find products to wrap around a neck for warmth.'),
 ('umbrella',['umbrella'],'Find products for keeping rain off while walking.'),
 ('wallet',['wallet'],'Find items for carrying banknotes and cards.'),
 ('purse',['purse'],'Find items for carrying coins in a handbag.'),
 ('notebook',['notebook'],'Find products with blank pages for writing notes.'),
 ('pencil',['pencil'],'Find items for drawing in erasable graphite.'),
 ('pen',[r'\bpen\b|\bpens\b'],'Find products for writing with ink.'),
 ('ruler',['ruler'],'Find items for measuring straight lines on paper.'),
 ('sticker',['sticker'],'Find products with adhesive decorative pictures.'),
 ('magnet',['magnet'],'Find items for attaching notes to a refrigerator.'),
 ('keyring',['key.?ring'],'Find products for keeping keys together.'),
 ('bunting',['bunting'],'Find items for hanging triangular flags at a party.'),
 ('birthday_card',['birthday','card'],'Find items with birthday greeting messages.'),
 ('christmas_stocking',['christmas','stocking'],'Find Christmas products shaped as hanging stockings.'),
 ('lantern',['lantern'],'Find products for holding a light in a portable lantern.'),
 ('clock',['clock'],'Find items for telling the time on a wall.'),
 ('mirror',['mirror'],'Find items with a reflective surface for looking at yourself.'),
 ('coaster',['coaster'],'Find products to place under a drinking glass.'),
 ('placemat',['place.?mat'],'Find items to protect a table underneath a dinner plate.'),
 ('apron',['apron'],'Find products worn over clothes while cooking.'),
 ('oven_glove',['oven','glove|mitt'],'Find items for protecting hands when handling hot oven trays.'),
 ('egg_cup',['egg','cup'],'Find products for holding a boiled egg upright.'),
 ('plate',['plate'],'Find items for serving a meal on a flat dish.'),
 ('bowl',['bowl'],'Find products for serving soup in a deep dish.'),
 ('cutlery',['cutlery'],'Find items described as cutlery for eating meals.'),
 ('scissors',['scissor'],'Find products for cutting paper with two blades.'),
 ('ribbon',['ribbon'],'Find items for tying decorative bows.'),
 ('bell',[r'\bbell'],'Find products that ring as a small bell.'),
 ('money_box',['money','box'],'Find items for saving loose coins.'),
 ('cake_stand',['cake','stand'],'Find products for displaying a cake on a raised stand.'),
]

def make_contract(corpus='data/corpus.json',database='data/retail.duckdb',target='evaluation/quality_v1.json'):
    output=Path(target)
    if output.exists():raise FileExistsError('Contract already frozen; do not overwrite after inspecting retrieval/model outputs')
    source=Path(corpus);docs=json.loads(source.read_text());by_id={x['id']:x for x in docs};tasks=[]
    for i,(group,patterns,question) in enumerate(TOPICS,1):
        relevant=sorted(x['id'] for x in docs if x['kind']=='source_description' and all(re.search(pattern,x['text'],re.I) for pattern in patterns))
        if not relevant:raise ValueError('No source reference for '+group+'; stop before freezing or model execution')
        tasks.append({'id':f'R{i:02}','split':'new_family_holdout','family':'product:'+group,'kind':'retrieval','retrieval_kind':'source_description','question':question,'reference_method':'all listed regex predicates over actual source description text; silver relevance','reference_patterns':patterns,'relevant_ids':relevant,'expected_route':'retrieve'})
    countries=['Belgium','Portugal','Switzerland','Norway','Finland','Denmark','Sweden','Austria']
    with duckdb.connect(database,read_only=True) as con:
        for i,country in enumerate(countries,1):
            metric='line_count' if i%2 else 'signed_value'
            sql='SELECT '+('count(*)' if metric=='line_count' else 'sum(quantity * unit_price)')+' FROM transactions WHERE country = ?'
            value=con.execute(sql,[country]).fetchone()[0]
            if value is None:raise ValueError('Missing country reference')
            tasks.append({'id':f'N{i:02}','split':'new_family_holdout','family':country+':'+metric,'kind':'numerical','question':metric+' for '+country,'expected_route':'metric','metric':metric,'country':country,'oracle_sql':sql,'parameters':[country],'reference_value':str(value)})
    old=json.loads(Path('evaluation/tasks.json').read_text())['tasks']
    refs={25:['contract:01'],26:['contract:01','contract:02'],27:['contract:02'],28:['contract:04'],29:['contract:05'],30:['contract:03'],31:['contract:06'],32:['contract:01']}
    for item in old:
        if item['kind']=='numerical':continue
        case={'id':item['id'],'split':'observed_regression','family':'observed:'+item['id'],'kind':item['kind'],'question':item['question'],'expected_route':'retrieve' if item['kind']=='retrieval' else 'decline'}
        if item['kind']=='retrieval':
            relevant=refs[int(item['id'][1:])]
            assert all(identity in by_id for identity in relevant)
            case.update(retrieval_kind='project_contract',relevant_ids=relevant,reference_method='AI-selected source-contract paragraphs; known regression family',rubric_terms=item['rubric_terms'])
        tasks.append(case)
    result={'version':1,'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'authorship':'AI-authored; no independent human review','status_at_freeze':'not evaluated; frozen before 3 November routing/prompt changes','corpus_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'corpus_documents':len(docs),'original_tasks_sha256':hashlib.sha256(Path('evaluation/tasks.json').read_bytes()).hexdigest(),'reference_scope':'Product regex labels are silver and may include bad source descriptions or omit semantically relevant alternatives. Literal source support is not semantic answer correctness. No labels fitted into model weights.','holdout_note':'40 product topics and 8 customer-country/metric groups not used in previous development probes; source documents are in the searchable index, as required for retrieval. 16 previously inspected source/safety cases are regressions and reported separately. Same AI author made questions/references and implementation; this is not an independent benchmark.','prior_development_topics_excluded':['strawberry jars','ceramic storage jars','bags'],'tasks':tasks}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    digest=hashlib.sha256(output.read_bytes()).hexdigest();output.with_suffix('.sha256').write_text(digest+'  '+output.name+'\n')
    print(json.dumps({'tasks':len(tasks),'new_family_holdout':sum(t['split']=='new_family_holdout' for t in tasks),'observed_regression':sum(t['split']=='observed_regression' for t in tasks),'sha256':digest}))
    return result
if __name__=='__main__':make_contract()
