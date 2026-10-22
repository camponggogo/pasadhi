"""Standardize the proposal to a five-month, milestone-gated $200k pre-seed plan."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'web/pitch'
plan=json.loads((folder/'financial-plan.json').read_text())
plan.update(runway_months=5,raise_usd=200000,operating_budget_usd=170000,contingency_usd=30000,
            monthly_operating_budget_usd=34000,proposed_instrument='Post-money valuation-cap SAFE; subject to jurisdiction and legal review',
            illustrative_post_money_cap_usd=2500000,illustrative_ownership_sold_percent=8,
            financing_status='Negotiation scenario, not a valuation appraisal or an executed offer')
for entry in plan['budget']:
    entry['amount']=round(200000*entry['percent']/100)
plan['milestone_gates']=[
 {'weeks':'1–4','evidence':'15 buyer interviews; three design-partner targets; two-host correctness/recovery'},
 {'weeks':'5–8','evidence':'Two paid pilots targeted; ten-host deployment and security review'},
 {'weeks':'9–16','evidence':'Measure workload ROI, conversion and support costs; expand only when gates pass'},
 {'weeks':'17–20','evidence':'Base ten paid sites; stretch eighteen; implement month-six lean cost plan'}]
plan['assumptions']=[s.replace('Month-seven','Month-six') for s in plan['assumptions']]
plan['dilution_sensitivity']=[{'post_money_cap_usd':cap,'raise_usd':200000,'ownership_sold_percent':200000/cap*100} for cap in (2000000,2500000,3000000)]
assert sum(x['amount'] for x in plan['budget'])==200000
assert sum(x['percent'] for x in plan['budget'])==100
assert plan['operating_budget_usd']/5==34000
(folder/'financial-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
deck=json.loads((folder/'deck.json').read_text(encoding='utf-8'))
for d in deck['slides']:
    for key in ('notes','takeaway','title','subtitle'):
        if key in d:
            d[key]=d[key].replace('six-month','five-month').replace('six months','five months').replace('month six','month five').replace('$240k','$200k').replace('240,000','200,000').replace('240k','200k').replace('6เดือน','5เดือน')
    if d['kind']=='ask':
        d['title']='$200k for five months of execution'
        d['takeaway']='Proposed post-money SAFE: $2.5M cap implies 8% for this $200k raise; terms subject to negotiation.'
        d['notes']='ข้อเสนอทุน200,000ดอลลาร์สำหรับ5เดือน:operating170,000และbuffer30,000 เฉลี่ย34,000ต่อเดือน เป้าฐาน10sitesยังขาดทุน18sitesเป็นstretchที่เริ่มบวกเมื่อfixedcostลดเหลือ24kเดือน6 เสนอpost-moneySAFEcap2.5Mเพื่อเจรจา200k/2.5M=8%ก่อนpricedroundในอนาคต ไม่ใช่valuationที่ประเมินอิสระหรือดีลที่ตกลงแล้ว'
        d['sources'].append('https://www.ycombinator.com/safe')
    elif d['kind']=='budget':
        d['title']='Five-month use of funds: $200,000'
        d['table']=[['Use','Amount','Share']]+[[x['use'],f"${x['amount']:,}",f"{x['percent']}%"] for x in plan['budget']]+[['Total','$200,000','100%']]
        d['takeaway']='$170k operating plan + $30k contingency; $34k/month before receipts. Budget release follows evidence gates.'
        d['notes']='งบ5เดือน:engineering80k,pilotdelivery40k,GTM30k,security/legal20k,buffer30k รวม200k Operating170k/5=34kต่อเดือน ต้องยืนยันใบเสนอราคาและสัญญาจ้างก่อนใช้เงินจริง โอนbufferเมื่อผ่านgateเท่านั้น'
    elif d['kind']=='sensitivity':
        d['takeaway']='50 paying nodes/site; $44.28 price; $16.37 direct cost; $24k fixed costs from month six. Scenarios, not forecast.'
        d['notes']=d['notes'].replace('เดือน7','เดือน6')
    elif d['kind']=='roadmap':
        d['items']=[['Now','M0 complete','Local app, kernel baseline and reproducible papers'],['Weeks 1–8','Technical gates','Two-host recovery, security review and two paid-pilot targets'],['Weeks 9–20','Commercial gates','Measure ROI; base ten sites; eighteen-site stretch target']]
        d['takeaway']='Five-month milestone plan; customer targets and multi-host capabilities require validation.'
    elif d['kind']=='gates':
        d['items']=[['Weeks 1–4','15 buyer interviews; three partner targets; two-host correctness'],['Weeks 5–8','Two paid-pilot targets; ten-host test and security gate'],['Weeks 9–20','Validate ROI; base ten sites; eighteen-site stretch; lean cost transition']]
        d['notes']='เป้าหมายทั้งหมดเป็นแผน20สัปดาห์ ไม่ใช่tractionจริง สัปดาห์1–4ลดproduct/demandrisk สัปดาห์5–8พิสูจน์pilotและsecurity สัปดาห์9–20วัดROIและขายก่อนขยายทีม หากไม่ผ่านgateลดburnก่อนใช้buffer'
if not any(d['kind']=='terms' for d in deck['slides']):
    deck['slides'].append({'kind':'terms','light':True,'title':'Financing terms: a negotiation framework',
       'table':[['Post-money cap','Proposed raise','Illustrative ownership'],['$2.0M','$200k','10.00%'],['$2.5M','$200k','8.00%'],['$3.0M','$200k','6.67%']],
       'takeaway':'Post-money SAFE illustration before future-round dilution; cap is not an independent appraisal. No YC affiliation implied.',
       'notes':'ใช้post-moneySAFEเป็นกรอบเริ่มเจรจาเท่านั้น สูตรเบื้องต้นคือinvestment/cap เงื่อนไขการconvert,optionpool,SAFEอื่นและpricedroundในอนาคตทำให้ownershipเปลี่ยนได้ YCstandarddealจริงคือ500kประกอบ125k7%และ375kuncappedMFNต่างจากข้อเสนอPASADHIนี้ ต้องตรวจjurisdictionและกฎหมายก่อนลงนาม',
       'sources':['https://www.ycombinator.com/safe','https://www.ycombinator.com/deal/','web/pitch/financial-plan.json']})
(folder/'deck.json').write_text(json.dumps(deck,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
memo=(folder/'funding-plan.md').read_text(encoding='utf-8')
for a,b in [('six-month','five-month'),('six months','five months'),('$240,000','$200,000'),('$204,000','$170,000'),('$96,000','$80,000'),('$48,000','$40,000'),('$36,000','$30,000'),('$24,000 | 10%','$20,000 | 10%'),('month-six','month-five'),('month-six','month-five'),('after month six','after month five'),('Month-seven','Month-six'),('$170,000, or $34,000/month','$170,000, or $34,000/month')]:
    memo=memo.replace(a,b)
start=memo.index('## Milestones and release gates')
end=memo.index('## Profit after the runway')
memo=memo[:start]+'''## Milestones and release gates

- Weeks 1–4: target 15 interviews and three design partners; demonstrate two-host correctness and recovery.
- Weeks 5–8: target two paid pilots; demonstrate a controlled ten-host setup and complete a security review.
- Weeks 9–16: measure real ROI, conversion and delivery costs; expand only when acceptance gates pass.
- Weeks 17–20: base target ten paying sites; stretch target eighteen; agree the lean fixed-cost plan for month six.
- Review budget and evidence every two weeks. A missed gate triggers scope reduction or slower hiring before contingency release.
- No customer target is represented as contracted, and no profitability probability is assigned without validated conversion data.

'''+memo[end:]
memo=memo.replace('post-runway fixed overhead reduced to **$24,000/month**','post-runway fixed overhead reduced to **$24,000/month** from month six')
memo += '''
## Proposed financing framework

Suggested negotiation starting point: **$200,000 on a post-money valuation-cap SAFE at an illustrative $2.5 million cap**. This implies **8%** ownership sold for this SAFE in the simplified cap calculation, before dilution from a future priced round. A cap is a negotiated conversion term, not an independent enterprise valuation.

| Post-money cap | Raise | Illustrative ownership sold |
|---|---:|---:|
| $2.0M | $200,000 | 10.00% |
| $2.5M | $200,000 | 8.00% |
| $3.0M | $200,000 | 6.67% |

Source for SAFE mechanics: https://www.ycombinator.com/safe
Jurisdiction, corporate structure, option pool, other SAFEs and conversion terms require review before signing. The standard YC accelerator deal is a separate $500k package ($125k for 7% plus $375k uncapped MFN SAFE); this PASADHI proposal is not that deal and does not imply YC admission or endorsement: https://www.ycombinator.com/deal/
'''
(folder/'funding-plan.md').write_text(memo,encoding='utf-8')
print('Standardized to 20 weeks, $200k total, $170k operating + $30k buffer; 23 slides.')
