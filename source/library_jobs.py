"""Current Buddy exports, all produced by the registered character renderer."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KIT=ROOT/'identity'
def jobs():
    result=[]
    def add(name,args):result.append({'name':name,'script':str(KIT/'blender/render_brand.py'),'args':args})
    views=[('buddy-avatar',1024,True),('buddy-ready',1400,True),('buddy-portrait',1400,True),('buddy-ready',1400,False),('buddy-explaining',1400,False),('buddy-thinking',1400,False),('buddy-explaining',1400,True),('buddy-thinking',1400,True),('buddy-front',1200,False),('buddy-side',1200,False),('buddy-portrait',1600,False),('buddy-feet',1200,False),('buddy-feet-side',1200,False),('buddy-hands',1200,False),('buddy-antlers',1400,False)]
    for view,size,alpha in views:
        add(view+('-transparent' if alpha else ''),['--view',view,'--size',str(size),'--samples','192']+(['--transparent'] if alpha else []))
    for name in ('welcoming','explaining','thinking','delighted','concerned','surprised','playful'):
        stem='expression-'+name+'-compact-transparent'
        result.append({'name':stem,'script':str(ROOT/'buddy/blender/render_buddy.py'),'args':['--view','avatar-compact','--expression',name,'--size','1024','--samples','192','--transparent','--output',str(KIT/f'renders/{stem}.png')]})
    for full,alpha in [(False,False),(False,True),(True,True)]:
        for name in ('welcoming','explaining','thinking','delighted','concerned','surprised','playful'):
            stem='expression-'+name+('-pose' if full else '')+('-transparent' if alpha else '')
            add(stem,['--view','buddy-ready' if full else 'buddy-avatar','--expression',name,'--size','1200','--samples','192','--output',str(KIT/f'renders/{stem}.png')]+(['--transparent'] if alpha else []))
    return result
