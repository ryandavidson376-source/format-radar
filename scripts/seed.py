"""Creates the clearly labeled, unranked starter playbook library."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# id|name|category|hook|steps|why|remix|keywords (comma-separated)
ROWS = """
before_after|Before / After|Visual|Wait until you see the difference.|Show the starting point; hint at the work; reveal the result.|A clear contrast creates an instant payoff.|Show your editing before/after or a room makeover.|before and after,before after,then vs now
transformation|30-Day Transformation|Storytelling|This is what changed in 30 days.|Set a baseline; show progress milestones; reveal the ending.|Time compression makes progress compelling.|Track a skill, physique, or creative project.|transformation,glow up,30 day,one month progress
pov|POV Scenario|Entertainment|POV: you're in this exact situation.|Establish a role; act out the recognizable moment; finish with a twist.|Viewers identify themselves in the scene.|POV of a beginner at a car meet.|pov,point of view
storytime|One-Minute Storytime|Storytelling|I still can't believe this happened.|Open mid-conflict; give context; escalate; land the ending.|Narrative tension rewards watching through.|Tell the story behind a difficult shoot.|storytime,story time,what happened to me
hot_take|Unpopular Opinion|Engagement|Unpopular opinion: everyone gets this wrong.|State the claim; justify it; show an example; invite debate.|A defensible disagreement encourages comments.|Challenge a popular fitness or editing tip.|unpopular opinion,hot take,controversial opinion
common_mistakes|Three Common Mistakes|Education|Stop making these three mistakes.|Show mistake one; explain why; repeat; end with the fix.|People watch to avoid making a costly error.|Show three camera settings new shooters misuse.|mistakes,stop doing,things you're doing wrong
quick_tutorial|60-Second Tutorial|Education|Here's how to do this in under a minute.|Show finished result; demonstrate steps; recap.|Fast practical utility makes the video saveable.|Teach a single Lightroom edit.|tutorial,how to,how-to,quick tutorial
step_by_step|Step-by-Step Walkthrough|Education|Copy these exact steps.|Define goal; number each step; show the finished result.|Removes ambiguity and makes the outcome repeatable.|Demonstrate a complete pre-shoot checklist.|step by step,step-by-step,walkthrough
myth_bust|Myth vs Fact|Education|You've probably been told this. It's wrong.|Repeat the myth; contrast evidence; demonstrate the truth.|Corrects a belief with a satisfying reversal.|Debunk a camera or nutrition misconception.|myth,debunk,misconception,fact vs fiction
reaction|Real-Time Reaction|Entertainment|My reaction to seeing this for the first time.|Establish the stimulus; show genuine reaction; give the takeaway.|Emotion is the center of the story.|React to a surprising car build.|reaction,reacting,reacts to
stitch_reply|Stitch / Video Reply|Engagement|This clip needs some context.|Show the original premise; respond directly; offer proof.|Builds on a familiar conversation.|Respond to a controversial car opinion.|stitch,duet,video reply,responding to
ranked_list|Ranking / Tier List|Engagement|I'm ranking these from worst to best.|Show criteria; rank quickly; defend the top pick.|Anticipation and disagreement drive watch time.|Rank five beginner photography lenses.|ranking,tier list,ranked
best_five|Top Five Picks|Education|These are my five favorites right now.|Show five options; give one reason each; identify a winner.|Clear curation saves viewer research.|Name five affordable photo locations.|top 5,top five,best five,5 best
side_by_side|Side-by-Side Comparison|Product|Same test. Two very different results.|Control the conditions; alternate examples; state the difference.|Visual evidence makes comparisons immediate.|Compare two editing styles on one shot.|vs,versus,comparison,compared
choose_one|This or That?|Engagement|You can only pick one.|Show two alternatives; give a quick distinction; ask viewers.|Low-friction participation prompts replies.|Ask viewers to choose between two car edits.|this or that,which one,would you rather
blind_test|Blind Test / Guessing Game|Engagement|Can you guess which one costs more?|Hide the answer; run the test; reveal at the end.|A curiosity gap keeps the reveal valuable.|Compare two lens photos without labels.|blind test,guess which,guess the,can you guess
product_demo|One-Feature Product Demo|Product|This tiny feature changes everything.|Show the problem; demonstrate a feature; show outcome.|Specificity beats generic promotion.|Show a clever photography accessory.|demo,feature test,product test
unboxing|Unboxing + First Impression|Product|Let's see if this lives up to the hype.|Show packaging; reveal; first hands-on reaction; early verdict.|Discovery and product curiosity create a simple arc.|Unbox a budget camera accessory.|unboxing,unbox,first impressions
honest_review|No-Hype Review|Product|Here's what nobody told me about this.|Set expectations; show strengths; show flaws; verdict.|A balanced judgment builds trust.|Review a lens after a week of use.|honest review,review,worth it
budget_luxury|Budget vs Luxury|Product|Does the expensive one actually win?|Introduce two price points; test fairly; compare results.|Challenges the assumption that price equals quality.|Budget lens versus premium lens shots.|cheap vs expensive,budget vs luxury,expensive vs cheap
behind_scenes|Behind the Scenes|Storytelling|Here's what it actually took to make this.|Start with finished output; rewind to setup; show decisions.|Reveals hidden effort and satisfies curiosity.|Show how a car photo was created.|behind the scenes,bts,how i made
my_day|Day in the Life|Lifestyle|A day in my life looks like this.|Start the day; show varied moments; finish with reflection.|A relatable sequence builds connection.|Show a day balancing work and shooting.|day in my life,day in the life,ditl
micro_vlog|Micro Vlog|Lifestyle|Come with me for the next 30 seconds.|Montage small moments; add text context; end on highlight.|Short personal slices feel effortless to watch.|Film one afternoon at a car meet.|mini vlog,micro vlog,vlog
morning_routine|Routine Breakdown|Lifestyle|Here's my current routine.|Show each step; include timing or tips; close with result.|Routines package practical habits in a repeatable format.|Share a pre-work shoot preparation routine.|routine,morning routine,night routine
challenge|Creator Challenge|Storytelling|I tried this challenge so you don't have to.|Define the constraint; show attempts; reveal the outcome.|A clear goal adds stakes and progression.|One lens, one location, ten car shots.|challenge,i tried,24 hours
countdown|Countdown Reveal|Engagement|Number one surprised me.|Introduce a ranked reveal; count down; finish on the strongest.|Delayed payoff makes the audience continue watching.|Count down the best five photos from a shoot.|countdown,number one,#1,top 10
process_timelapse|Timelapse Process|Visual|Watch the entire process in 20 seconds.|Show setup; speed up progression; linger on final result.|Compresses an otherwise slow transformation.|Timelapse a full editing session.|timelapse,time lapse,speedrun
satisfying|Satisfying Process|Visual|This result is ridiculously satisfying.|Show repetitive process; keep visuals clean; reveal completion.|Sensory payoff works without much explanation.|Show meticulous car detailing or color grading.|satisfying,oddly satisfying,restoration
asmr|ASMR / Sound Detail|Visual|Turn your sound on for this.|Capture crisp tactile sounds; minimize speech; end cleanly.|Sound and texture create an immersive payoff.|Record mechanical clicks and detailing sounds.|asmr,no talking,relaxing sounds
seamless_loop|Seamless Loop|Visual|Watch how the ending connects to the start.|Plan matching opening and closing frames; cut on action.|A seamless ending invites a replay.|Loop a car door close into a new angle.|loop,seamless loop,perfect loop
cinematic_reveal|Cinematic Reveal|Visual|Wait for the full reveal.|Start in tight detail; widen with movement; reveal the hero shot.|Controlled withholding amplifies the reveal.|Reveal a car through details before the wide shot.|cinematic,reveal,car edit
gear_dump|What's in My Bag|Lifestyle|Everything I use fits in this bag.|Lay out essentials; quick reason for each; show full kit.|Viewers borrow ready-made setups.|Show your compact camera kit.|what's in my bag,edc,gear list,my setup
beginner_pro|Beginner vs Pro|Education|Here's the difference experience makes.|Show beginner approach; contrast expert approach; explain one lever.|Contrast makes the lesson obvious.|Same car: novice vs experienced framing.|beginner vs pro,beginner vs expert,amateur vs pro
expectation_reality|Expectation vs Reality|Entertainment|What I expected vs what actually happened.|Show idealized expectation; hard cut to real outcome.|A familiar mismatch creates relatable humor.|Expectation vs reality of car photography.|expectation vs reality,expectations vs reality
relatable_sketch|Relatable Sketch|Entertainment|You know you're one of us when…|Establish a familiar situation; exaggerate; land a punchline.|Specific shared frustrations build community.|A skit about editing until 2 a.m.|skit,sketch,relatable,when you
meme_remix|Meme Remix|Entertainment|This meme is painfully accurate.|Start from a recognizable meme structure; adapt to niche.|Recognition lets you communicate quickly.|Remix a meme around gear obsession.|meme,template,trend meme
trending_audio|Trending-Audio Interpretation|Entertainment|I had to make my own version of this sound.|Apply a recognizable sound to a niche-specific scenario.|Sound familiarity provides an entry point.|Apply a popular audio to shoot prep.|trending sound,trending audio,using this sound
screen_capture|Screen Recording Tutorial|Education|Watch me fix this in real time.|Start from the problem screen; demonstrate clicks; compare result.|On-screen proof reduces friction.|Show editing adjustments step by step.|screen recording,screen record,screen tutorial
commentary_overlay|Green-Screen Commentary|Education|We need to talk about this.|Place visual context behind speaker; explain reaction or lesson.|Context stays visible while the creator interprets it.|Analyze a photo composition on screen.|green screen,greenscreen,commentary
visual_explainer|Visual Explainer|Education|Here's why this actually happens.|Present a question; explain with diagrams or examples; summarize.|Simplifies complex ideas with visible scaffolding.|Explain why a polarizer changes reflections.|explained,how it works,visual explanation
surprising_fact|Surprising Fact|Education|This sounds fake, but it's real.|State counterintuitive fact; provide context; give source or proof.|A surprising fact creates a knowledge gap.|Explain an unexpected automotive fact.|did you know,fun fact,interesting fact
quiz|Three-Second Quiz|Engagement|You've got three seconds to answer.|Ask question; pause; reveal answer; quick explanation.|The viewer participates instead of passively watching.|Guess the camera focal length from a photo.|quiz,trivia,test your knowledge
street_interview|Street Interview|Engagement|I asked strangers one question.|Ask the same concise question; collect quick contrasting answers.|Unscripted responses create social curiosity.|Ask enthusiasts their dream car.|street interview,asking strangers,interview
qa|Rapid-Fire Q&A|Education|Answering your most-asked questions.|Read a question; answer directly; repeat for several.|Useful answers accumulate into a high-value clip.|Answer photography questions in rapid succession.|q&a,questions answered,answering questions
comment_reply|Comment-to-Video Reply|Engagement|Someone asked me this, so here's the answer.|Show a viewer question; demonstrate response; invite next request.|Turns the audience into a content engine.|Answer a follower's camera question.|replying to,comment asked,you asked
client_result|Client Result Story|Storytelling|Here's what we delivered and how.|Introduce goal; show process; present result and constraint.|Concrete outcomes build credibility.|Tell the story of a successful car shoot.|client result,case study,customer result
voiceover_breakdown|Voiceover Breakdown|Education|Here's exactly what you're seeing.|Play footage; narrate key decisions; end with takeaway.|Explanation adds meaning to ordinary footage.|Narrate how you composed a car shot.|voiceover,breakdown,voice over
text_only_story|Text-on-Screen Story|Storytelling|Read this before the clip ends.|Use captivating first caption; reveal next beats visually; close.|Silent-friendly captions create a reading loop.|Tell a short shoot mishap over B-roll.|text on screen,caption story,read this
one_tip|One Tip That Helps|Education|One tiny change that makes a huge difference.|Show before; give one actionable tip; show after.|Low cognitive load makes advice usable.|Share one camera framing tip.|one tip,quick tip,pro tip,small trick
life_hack|Unexpected Hack|Education|I wish I'd learned this sooner.|Demonstrate an unusual shortcut; verify result; note limitations.|Novel usefulness encourages saves.|Show a useful photography gear hack.|life hack,hack,shortcut
""".strip().splitlines()

def build_taxonomy():
    entries = []
    for row in ROWS:
        parts = row.split('|')
        assert len(parts) == 8, (len(parts), row)
        id_, name, category, hook, steps, why, remix, keywords = parts
        entries.append(dict(id=id_, name=name, category=category, hook=hook,
                            steps=steps.split('; '), why=why, remix=remix,
                            keywords=[w.strip() for w in keywords.split(',')]))
    assert len(entries) == 50
    assert len({x['id'] for x in entries}) == 50
    return entries

if __name__ == '__main__':
    entries = build_taxonomy()
    (ROOT/'scripts'/'taxonomy.json').write_text(json.dumps(entries, indent=2, ensure_ascii=False)+'\n')
    demo = {
        'schema_version': 1, 'mode': 'demo', 'month': 'demo',
        'period_label': 'Starter playbook library', 'generated_at': '2026-11-09T00:00:00Z',
        'window_start': None, 'window_end': None, 'platforms': [],
        'sample_size': 0, 'query_count': 0, 'niches_covered': 0,
        'note': 'These 50 examples are NOT ranked or based on measured views. Run the monthly collection with an API key for verified video evidence and scores.',
        'results': [dict(entry, rank=None, score=None, confidence=None, niche='All niches',
                          stats={'videos': 0, 'creators': 0, 'views': 0,
                                 'avg_views': 0, 'engagement_pct': 0, 'views_per_day': 0},
                          sample_videos=[]) for entry in entries],
    }
    (ROOT/'site'/'data'/'latest.json').write_text(json.dumps(demo, indent=2, ensure_ascii=False)+'\n')
    (ROOT/'site'/'data'/'index.json').write_text(json.dumps({'latest':'demo','snapshots':[]},indent=2)+'\n')
    print('Created 50 starter playbooks and demo dataset')
