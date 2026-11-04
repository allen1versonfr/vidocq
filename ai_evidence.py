"""Finite evidence selections: the model never needs to reconstruct a URL or quote."""
from profile_registry import url_tokens,canonical_reference
import re
from itertools import zip_longest

def selections(records):
    spans={};links={};span_groups=[];link_groups=[]
    for record in records:
        text=record['excerpt']
        span_group=[];link_group=[]
        for i,start in enumerate(range(0,len(text),350),1):
            quote=text[start:start+350]
            if len(quote.strip())>=10:span_group.append((record['id']+'-S'+str(i),{'citation':record['id'],'quote':quote,'reference':record['reference']}))
        for i,url in enumerate(url_tokens(text),1):
            if url.startswith('https://'):link_group.append((record['id']+'-L'+str(i),{'citation':record['id'],'url':url}))
        span_groups.append(span_group);link_groups.append(link_group)
    for group in zip_longest(*span_groups):
        for item in group:
            if item and len(spans)<24:spans[item[0]]=item[1]
    for group in zip_longest(*link_groups):
        for item in group:
            if item and len(links)<40:links[item[0]]=item[1]
    return spans,links

def independent(left,right):
    try:return canonical_reference(left)!=canonical_reference(right)
    except ValueError:return False

def validate(result,mode,records,plan,spans,links,next_steps):
    """Item isolation plus legacy import compatibility; new prompts use IDs only."""
    lookup={r['id']:r for r in records};rejected=[]
    def bad(message):raise ValueError(message)
    def finish(output,source_items,accepted):
        if source_items and rejected and not accepted:raise ValueError(rejected[0]['reason'])
        output.update(mode=mode,draft=True,rejected_items=rejected)
        return output
    if mode in ('queries','planning'):
        indexes=result.get('indexes')
        if not isinstance(indexes,list) or len(indexes)>(8 if mode=='planning' else 5):bad('Invalid query selection.')
        good=[]
        for i in indexes:
            if type(i) is int and 0<=i<len(plan):
                if i not in good:good.append(i)
            else:rejected.append({'reason':'Unknown query selection.'})
        return finish({'queries':[plan[i] for i in good],'notice':'Finite query selections; no ownership conclusion.'},indexes,good)
    if mode=='leads':
        items=result.get('link_ids',result.get('leads'));good=[]
        if not isinstance(items,list) or len(items)>5:bad('Invalid link selection.')
        for item in items:
            try:
                if isinstance(item,str):
                    if item not in links:bad('Unknown explicit link ID.')
                    lead=links[item]
                else:
                    if not isinstance(item,dict) or item.get('citation') not in lookup:bad('Unknown link citation.')
                    lead=item
                    if lead.get('url') not in url_tokens(lookup[lead['citation']]['excerpt']):bad('Link is not a complete URL in cited evidence.')
                from discovery_tools import public_url
                url=public_url(lead['url']);good.append({'citation':lead['citation'],'url':url})
            except (ValueError,TypeError,KeyError) as e:rejected.append({'reason':str(e)})
        return finish({'leads':good,'notice':'Complete explicit source links only; ownership remains unverified.'},items,good)
    if mode=='assessment':
        items=result.get('comparisons');steps=result.get('next_step_indexes',[]);good=[]
        if not isinstance(items,list) or len(items)>4 or not isinstance(steps,list) or len(steps)>20:bad('Invalid assessment selection.')
        valid_steps=[]
        for step in steps:
            if isinstance(step,str) and re.fullmatch(r'[0-9]',step):step=int(step)
            if type(step) is int and 0<=step<len(next_steps):
                if step in valid_steps:continue
                if len(valid_steps)<3:valid_steps.append(step)
                else:rejected.append({'reason':'Next evidence action limit reached; extra suggestion omitted.'})
            else:rejected.append({'reason':'Unknown next evidence action.'})
        for item in items:
            try:
                if not isinstance(item,dict) or item.get('type') not in ('agreement','difference'):bad('Invalid comparison type.')
                if 'selection_ids' in item:
                    chosen=item['selection_ids']
                    if not isinstance(chosen,list) or len(chosen)!=2 or any(not isinstance(i,str) or i not in spans for i in chosen):bad('Unknown comparison excerpt ID.')
                    selected=[spans[i] for i in chosen];ids=[x['citation'] for x in selected];quotes=[x['quote'] for x in selected]
                else:
                    ids=item.get('citations');quotes=item.get('quotes')
                if not isinstance(ids,list) or len(ids)!=2 or any(not isinstance(i,str) or i not in lookup for i in ids) or ids[0]==ids[1]:bad('Comparison requires two different eligible citations.')
                if not isinstance(quotes,list) or len(quotes)!=2 or any(not isinstance(q,str) or not 10<=len(q)<=400 or q not in lookup[i]['excerpt'] for i,q in zip(ids,quotes)):bad('Comparison contains an unsupported quotation.')
                if 'selection_ids' not in item:
                    text=item.get('explanation','');source=' '.join(lookup[i]['excerpt'] for i in ids)
                    if not isinstance(text,str) or not text or re.search(r'(?i)(belongs to|owned by|confirmed identity|definitely the same|is guilty)',text) or any(t not in source for t in re.findall(r'https?://\S+|\b\S+@\S+\.\S+|\b\d[\d.,%-]*\b',text)):bad('Unsupported comparison assertion.')
                diverse=independent(lookup[ids[0]]['reference'],lookup[ids[1]]['reference'])
                good.append({'type':item['type'],'citations':ids,'quotes':quotes,'independent_sources':diverse,'explanation':'Compare the cited excerpts; account ownership and a relationship are not established.'})
            except (ValueError,TypeError,KeyError) as e:rejected.append({'reason':str(e)})
        return finish({'comparisons':good,'next_steps':[next_steps[i] for i in dict.fromkeys(valid_steps)],'notice':'Review proposals only; source diversity is not identity verification.'},items+steps,good+valid_steps)
    items=result.get('selection_ids',result.get('claims'));good=[]
    if not isinstance(items,list) or len(items)>6:bad('Invalid evidence selection.')
    for item in items:
        try:
            if isinstance(item,str):
                if item not in spans:bad('Unknown source excerpt ID.')
                claim=dict(spans[item])
            else:
                if not isinstance(item,dict) or not isinstance(item.get('citation'),str) or item['citation'] not in lookup:bad('Unknown citation; draft rejected.')
                record=lookup[item['citation']];quote=item.get('quote')
                if not isinstance(quote,str) or not 10<=len(quote)<=600 or quote not in record['excerpt']:bad('Unsupported quotation; draft rejected.')
                if mode=='synthesis':
                    text=item.get('text','')
                    if not isinstance(text,str) or not text or re.search(r'(?i)(belongs to|owned by|confirmed identity|definitely the same|is guilty)',text):bad('Unsupported identity assertion.')
                    if any(t not in record['excerpt'] for t in re.findall(r'https?://\S+|\b\S+@\S+\.\S+|\b\d[\d.,%-]*\b',text)):bad('Unsupported identifiers or numbers.')
                claim={'citation':record['id'],'quote':quote,'reference':record['reference']}
            if re.search(r'(?i)(matching handle.*not proof|ownership.*unverified|relevance and ownership remain)',claim['quote']):continue
            if mode=='synthesis':claim['text']='Source excerpt selected for review; no relationship or ownership inference is established.'
            good.append(claim)
        except (ValueError,TypeError,KeyError) as e:rejected.append({'reason':str(e)})
    # Boilerplate-only selections are a valid abstention, not a failed claim.
    return finish({'claims':good,'notice':'Model-selected source excerpts for review; no verified identity or factual accuracy claim.'},items,good)
