"""Use researched 24-month runway guidance and a separate five-month delivery milestone."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'web/pitch'
plan=json.loads((folder/'financial-plan.json').read_text())
sources=['https://www.ycombinator.com/blog/how-to-raise-a-seed-round/',
         'https://carta.com/uk/en/learn/startups/fundraising/',
         'https://www.crv.com/content/when-to-raise-series-a']
plan.update(runway_months=24,delivery_milestone_months=5,raise_usd=750000,operating_budget_usd=637500,
            contingency_usd=112500,monthly_operating_budget_usd=26562.50,
            staged_operating_cost_usd=626000,one_off_delivery_reserve_usd=11500,
            monthly_cost_schedule=[{'months':'1–5','count':5,'monthly_fixed_cost_usd':34000},
                                   {'months':'6–24','count':19,'monthly_fixed_cost_usd':24000}],
            illustrative_post_money_cap_usd=5000000,illustrative_ownership_sold_percent=15,
            runway_sources=sources,
            alternative_18_month_raise_usd=600000)
for entry in plan['budget']:
    if entry['use']=='Engineering':entry['percent']=45
    elif entry['use']=='Pilot delivery + QA':entry['percent']=15
    entry['amount']=round(750000*entry['percent']/100)
plan['milestone_gates']=[
 {'months':'1–5','evidence':'15 interviews, three design-partner targets, two paid-pilot targets, two/ten-host recovery tests'},
 {'months':'6–12','evidence':'Validate paid retention, support cost and one repeatable workload; target ten paid sites'},
 {'months':'13–18','evidence':'Target eighteen paid sites and verify lean unit economics; review next-round readiness'},
 {'months':'19–24','evidence':'Repeatable renewals and sales; stretch twenty-five sites; preserve fundraising optionality'}]
plan['assumptions']=[s.replace('Month-six','Month-six') for s in plan['assumptions']]
plan['dilution_sensitivity']=[{'post_money_cap_usd':cap,'raise_usd':750000,'ownership_sold_percent':750000/cap*100} for cap in (3750000,5000000,7500000)]
assert sum(x['amount'] for x in plan['budget'])==750000
assert sum(x['percent'] for x in plan['budget'])==100
assert 5*34000+19*24000+11500+112500==750000
(folder/'financial-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
deck=json.loads((folder/'deck.json').read_text(encoding='utf-8'))
for d in deck['slides']:
    if d['kind']=='ask':
        d['title']='$750k for a repeatable, paid compute product'
        d['subtitle']='24-month runway · first product and pilot gates in five months'
        d['items']=[['Product gate','Two-host recovery, ten-host validation and real-workload ROI'],['Commercial gate','Ten paid sites by month 12; eighteen-site profit gate targeted by month 18']]
        d['takeaway']='Proposed raise. Customer targets are unvalidated; revenue is excluded from the base cash-runway calculation.'
        d['notes']='ทุน750kสำหรับ24เดือน แยกmilestoneproduct/pilot5เดือนแรก คำนวณ5×34k+19×24k=626k บวกone-offreserve11.5kและcontingency112.5kรวม750k ไม่สมมติรายได้เพื่อยืดrunway ต้นทุนลูกค้าที่เพิ่มต้องเก็บเงินให้ครอบคลุมและตรวจcashflowจริง ไม่ตั้งrunway5เดือนอีกแล้ว'
        d['sources']=['web/pitch/financial-plan.json','web/pitch/funding-plan.md']+sources
    elif d['kind']=='budget':
        d['title']='24-month use of funds: $750,000'
        d['table']=[['Use','Amount','Share']]+[[x['use'],f"${x['amount']:,}",f"{x['percent']}%"] for x in plan['budget']]+[['Total','$750,000','100%']]
        d['takeaway']='$626k staged operations + $11.5k deployment reserve + $112.5k contingency. No revenue assumed for runway.'
        d['notes']='Budget45%engineering337.5k,15%pilot112.5k,15%GTM112.5k,10%security/legal75k,15%buffer112.5k Operatingรวม637.5kรองรับfixedcost626kและoneoff11.5k งบเป็นข้อเสนอ ต้องทดสอบต้นทุนจริงก่อนจ้าง'
    elif d['kind']=='sensitivity':
        d['takeaway']='Steady-state scenarios: $44.28 price; $16.37/node direct cost; $24k/month fixed overhead from month six. Not a forecast.'
        d['notes']='กำไรเป็นscenarioไม่ใช่คำรับประกันหลัง24เดือน:10sitesขาดทุน10045,18sitesบวก1119,25sitesบวก10887.5ต่อเดือน ขั้นต้นก่อนภาษีและข้อยกเว้น Break-even860payingnodesหรือ18sitesถ้า50nodes/site การคงfixedcost24kต้องทำตามแผนจริง'
    elif d['kind']=='roadmap':
        d['items']=[['Months 1–5','Product + pilot','Recovery tests, one real workload and two paid-pilot targets'],['Months 6–12','Repeatability','Ten paid-site target; verify retention and support cost'],['Months 13–24','Economics + growth','Eighteen-site profit gate; renewal evidence and next-round readiness']]
        d['takeaway']='First delivery in five months; cash runway planned for 24 months. All customer milestones are targets.'
        d['notes']='ระยะส่งมอบไม่เท่ากับrunway:product/pilot5เดือน เงินสด24เดือน เดือน6–12ตรวจการจ่ายซ้ำจริง เดือน13–24พิสูจน์unit economicsและrenewals เตรียมระดมทุนครั้งต่อไปเมื่อยังมีเงินเหลือพอ ไม่รอเงินหมด'
    elif d['kind']=='market-context':
        d['notes']=d['notes'].replace('ทุน200kมาจากงบmilestone5เดือน','ทุน750kมาจากงบrunway24เดือนและmilestone5เดือนแรก')
    elif d['kind']=='gates':
        d['title']='Separate delivery gates from cash runway'
        d['items']=[['Months 1–5','Two paid-pilot targets; validate workload ROI and recovery'],['Months 6–12','Ten paid-site target; validate retention and support burden'],['Months 13–24','Eighteen-site profit gate; renewals and next-round readiness']]
        d['takeaway']='Review evidence and cash monthly. Missed gates trigger scope or hiring changes before contingency release.'
        d['notes']='แผน24เดือนมีproductmilestone5เดือนแรก แบ่งreleasecapitalตามหลักฐาน ไม่สับสนaccelerator3เดือนหรือpilot4สัปดาห์กับrunwayบริษัท Targetทั้งหมดไม่ใช่signedpipeline'
    elif d['kind']=='terms':
        d['table']=[['Post-money cap','Proposed raise','Illustrative ownership'],['$3.75M','$750k','20.00%'],['$5.0M','$750k','15.00%'],['$7.5M','$750k','10.00%']]
        d['notes']='ตัวอย่างการเจรจา750kที่cap5Mเท่ากับ15%ตามสูตรเบื้องต้น ไม่ใช่บริษัทมีvaluation5Mที่ตลาดรับรอง ต้องตรวจSAFEอื่น,optionpoolและfuture-round dilution YCstandarddeal500kต่างจากแผน750kของPASADHI และไม่อ้างYCendorsement'
if not any(d['kind']=='runway-research' for d in deck['slides']):
    deck['slides'].append({'kind':'runway-research','light':True,'title':'Runway guidance has moved beyond a short pilot',
      'table':[['Source','Guidance','Planning use'],['YC seed guide','12–18 months','Older milestone-based baseline'],['Carta / CRV guidance','24–30 months','Allow for longer funding intervals'],['PASADHI proposal','24 months','Five-month delivery gate within longer cash runway']],
      'takeaway':'Guidance is not a universal rule or observed runway median. Financing needs follow milestones and cash costs.',
      'notes':'Researchตรวจ23ต.ค.2026:YCguideเดิมกล่าว12–18เดือน ขณะที่CartaและCRVแนะนำ24–30เดือน ไม่เรียกตัวเลขนี้ว่าmedianrunwayเพราะเป็นguidance ช่วงห่างรอบทุนที่วัดได้ไม่เท่ากับระยะเวลาที่ใช้pitch กรณีPASADHIเลือก24เดือนเป็นbaseline18เดือนเป็นแผนscopeเล็กและ6เดือนเป็นเพียงmilestone',
      'sources':sources})
(folder/'deck.json').write_text(json.dumps(deck,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Rebased to 24 months cash runway, five-month first delivery, $750k proposed raise; 24 slides.')
