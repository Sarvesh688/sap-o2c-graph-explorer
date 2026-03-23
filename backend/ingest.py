"""
ingest.py — Load all 19 SAP O2C entities into Neo4j AuraDB
Usage: python ingest.py
Place your data folders inside ../data/ directory
"""

import json
import os
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

DATA = Path("../data")


def load_jsonl(folder_name: str) -> list:
    records = []
    folder = DATA / folder_name
    if not folder.exists():
        print(f"  ⚠  Folder not found: {folder}")
        return records
    for f in sorted(folder.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    print(f"  Loaded {len(records):>6,} records  ←  {folder_name}/")
    return records


def create_indexes(s):
    for cypher in [
        "CREATE INDEX IF NOT EXISTS FOR (n:BusinessPartner) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:SalesOrder) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:SalesOrderItem) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Delivery) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:DeliveryItem) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:BillingDocument) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:BillingDocument) ON (n.accountingDocument)",
        "CREATE INDEX IF NOT EXISTS FOR (n:BillingItem) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Payment) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:JournalEntry) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Product) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Plant) ON (n.id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Address) ON (n.id)",
    ]:
        s.run(cypher)
    print("  Indexes ready.")


def ingest():
    print("\n🚀  Starting Neo4j ingestion\n")
    with driver.session() as s:

        print("── Indexes ──────────────────────────────")
        create_indexes(s)

        print("\n── Master data ──────────────────────────")

        # Business Partners
        for r in load_jsonl("business_partners"):
            s.run("""
                MERGE (bp:BusinessPartner {id: $id})
                SET bp.name=$name, bp.category=$cat,
                    bp.grouping=$grp, bp.firstName=$fn,
                    bp.lastName=$ln, bp.creationDate=$cd
            """, id=r["businessPartner"],
                 name=r.get("businessPartnerFullName",""),
                 cat=r.get("businessPartnerCategory",""),
                 grp=r.get("businessPartnerGrouping",""),
                 fn=r.get("firstName",""), ln=r.get("lastName",""),
                 cd=str(r.get("creationDate","")))

        # Addresses
        for r in load_jsonl("business_partner_addresses"):
            s.run("""
                MERGE (a:Address {id: $id})
                SET a.city=$city, a.country=$country, a.region=$region,
                    a.postalCode=$pc, a.street=$street, a.timeZone=$tz
                WITH a
                MATCH (bp:BusinessPartner {id: $bpId})
                MERGE (bp)-[:HAS_ADDRESS]->(a)
            """, id=r["businessPartner"]+"_"+r.get("addressId",""),
                 city=r.get("cityName",""), country=r.get("country",""),
                 region=r.get("region",""), pc=r.get("postalCode",""),
                 street=r.get("streetName",""), tz=r.get("addressTimeZone",""),
                 bpId=r["businessPartner"])

        # Products
        for r in load_jsonl("products"):
            s.run("""
                MERGE (p:Product {id: $id})
                SET p.type=$type, p.group=$grp, p.baseUnit=$bu,
                    p.division=$div, p.grossWeight=$gw,
                    p.netWeight=$nw, p.weightUnit=$wu
            """, id=r["product"], type=r.get("productType",""),
                 grp=r.get("productGroup",""), bu=r.get("baseUnit",""),
                 div=r.get("division",""), gw=str(r.get("grossWeight","")),
                 nw=str(r.get("netWeight","")), wu=r.get("weightUnit",""))

        # Product descriptions (EN only)
        for r in load_jsonl("product_descriptions"):
            if r.get("language") == "EN":
                s.run("""
                    MATCH (p:Product {id: $id})
                    SET p.description = $desc
                """, id=r["product"], desc=r.get("productDescription",""))

        # Plants
        for r in load_jsonl("plants"):
            s.run("""
                MERGE (pl:Plant {id: $id})
                SET pl.name=$name, pl.salesOrganization=$so,
                    pl.distributionChannel=$dc, pl.division=$div
            """, id=r["plant"], name=r.get("plantName",""),
                 so=r.get("salesOrganization",""),
                 dc=r.get("distributionChannel",""),
                 div=r.get("division",""))

        # Product → Plant storage
        for r in load_jsonl("product_plants"):
            s.run("""
                MATCH (p:Product {id: $pId})
                MATCH (pl:Plant {id: $plId})
                MERGE (p)-[:STORED_AT]->(pl)
            """, pId=r["product"], plId=r["plant"])

        # Product storage locations (enriches Plant nodes, skip huge volume)
        # We just capture the plant link — product_storage_locations has 16k rows
        # already covered by product_plants above

        # Customer company assignments
        for r in load_jsonl("customer_company_assignments"):
            s.run("""
                MATCH (bp:BusinessPartner {id: $id})
                SET bp.companyCode=$cc, bp.reconciliationAccount=$ra,
                    bp.customerAccountGroup=$cag
            """, id=r["customer"], cc=r.get("companyCode",""),
                 ra=r.get("reconciliationAccount",""),
                 cag=r.get("customerAccountGroup",""))

        # Customer sales area assignments
        for r in load_jsonl("customer_sales_area_assignments"):
            s.run("""
                MATCH (bp:BusinessPartner {id: $id})
                SET bp.salesOrganization=$so, bp.paymentTerms=$pt,
                    bp.shippingCondition=$sc, bp.incoterms=$inc
            """, id=r["customer"], so=r.get("salesOrganization",""),
                 pt=r.get("customerPaymentTerms",""),
                 sc=r.get("shippingCondition",""),
                 inc=r.get("incotermsClassification",""))

        print("\n── Transactional data ───────────────────")

        # Sales Order Headers
        for r in load_jsonl("sales_order_headers"):
            s.run("""
                MERGE (so:SalesOrder {id: $id})
                SET so.type=$type, so.salesOrg=$salesOrg,
                    so.amount=toFloat($amount), so.currency=$currency,
                    so.deliveryStatus=$ds, so.billingStatus=$bs,
                    so.creationDate=$cd, so.soldToParty=$stp,
                    so.paymentTerms=$pt, so.incoterms=$inc,
                    so.incotermsLocation=$incLoc
                WITH so
                OPTIONAL MATCH (bp:BusinessPartner {id: $stp})
                FOREACH (_ IN CASE WHEN bp IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (so)-[:SOLD_TO]->(bp)
                )
            """, id=r["salesOrder"], type=r.get("salesOrderType",""),
                 salesOrg=r.get("salesOrganization",""),
                 amount=r.get("totalNetAmount","0"),
                 currency=r.get("transactionCurrency",""),
                 ds=r.get("overallDeliveryStatus",""),
                 bs=r.get("overallOrdReltdBillgStatus",""),
                 cd=str(r.get("creationDate","")),
                 stp=r.get("soldToParty",""),
                 pt=r.get("customerPaymentTerms",""),
                 inc=r.get("incotermsClassification",""),
                 incLoc=r.get("incotermsLocation1",""))

        # Sales Order Items
        for r in load_jsonl("sales_order_items"):
            s.run("""
                MERGE (soi:SalesOrderItem {id: $id})
                SET soi.salesOrder=$soId, soi.itemNumber=$itemNo,
                    soi.material=$mat, soi.quantity=toFloat($qty),
                    soi.unit=$unit, soi.amount=toFloat($amt),
                    soi.currency=$cur, soi.plant=$plant,
                    soi.materialGroup=$mg
                WITH soi
                MATCH (so:SalesOrder {id: $soId})
                MERGE (so)-[:HAS_ITEM]->(soi)
                WITH soi
                OPTIONAL MATCH (p:Product {id: $mat})
                FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (soi)-[:REFERENCES_PRODUCT]->(p)
                )
            """, id=r["salesOrder"]+"_"+r["salesOrderItem"],
                 soId=r["salesOrder"], itemNo=r["salesOrderItem"],
                 mat=r.get("material",""), qty=r.get("requestedQuantity","0"),
                 unit=r.get("requestedQuantityUnit",""),
                 amt=r.get("netAmount","0"),
                 cur=r.get("transactionCurrency",""),
                 plant=r.get("productionPlant",""),
                 mg=r.get("materialGroup",""))

        # Sales Order Schedule Lines (enrich SalesOrderItem)
        for r in load_jsonl("sales_order_schedule_lines"):
            s.run("""
                MATCH (soi:SalesOrderItem {id: $id})
                SET soi.confirmedDeliveryDate=$cdd,
                    soi.confirmedQty=toFloat($qty)
            """, id=r["salesOrder"]+"_"+r["salesOrderItem"],
                 cdd=str(r.get("confirmedDeliveryDate","")),
                 qty=r.get("confdOrderQtyByMatlAvailCheck","0"))

        # Delivery Headers
        for r in load_jsonl("outbound_delivery_headers"):
            s.run("""
                MERGE (d:Delivery {id: $id})
                SET d.creationDate=$cd, d.shippingPoint=$sp,
                    d.pickingStatus=$ps, d.goodsMovementStatus=$gms,
                    d.deliveryBlockReason=$dbr
            """, id=r["deliveryDocument"],
                 cd=str(r.get("creationDate","")),
                 sp=r.get("shippingPoint",""),
                 ps=r.get("overallPickingStatus",""),
                 gms=r.get("overallGoodsMovementStatus",""),
                 dbr=r.get("deliveryBlockReason",""))

        # Delivery Items
        for r in load_jsonl("outbound_delivery_items"):
            s.run("""
                MERGE (di:DeliveryItem {id: $id})
                SET di.deliveryDocument=$dId, di.itemNumber=$itemNo,
                    di.quantity=toFloat($qty), di.unit=$unit,
                    di.plant=$plant, di.storageLocation=$sl,
                    di.referenceOrder=$refSo,
                    di.referenceOrderItem=$refSoItem
                WITH di
                MATCH (d:Delivery {id: $dId})
                MERGE (d)-[:HAS_ITEM]->(di)
                WITH di
                OPTIONAL MATCH (so:SalesOrder {id: $refSo})
                FOREACH (_ IN CASE WHEN so IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (di)-[:FULFILLS]->(so)
                )
                WITH di
                OPTIONAL MATCH (pl:Plant {id: $plant})
                FOREACH (_ IN CASE WHEN pl IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (di)-[:SHIPPED_FROM]->(pl)
                )
            """, id=r["deliveryDocument"]+"_"+r["deliveryDocumentItem"],
                 dId=r["deliveryDocument"], itemNo=r["deliveryDocumentItem"],
                 qty=r.get("actualDeliveryQuantity","0"),
                 unit=r.get("deliveryQuantityUnit",""),
                 plant=r.get("plant",""), sl=r.get("storageLocation",""),
                 refSo=r.get("referenceSdDocument",""),
                 refSoItem=r.get("referenceSdDocumentItem",""))

        # Billing Document Headers
        for r in load_jsonl("billing_document_headers"):
            s.run("""
                MERGE (b:BillingDocument {id: $id})
                SET b.type=$type, b.amount=toFloat($amt),
                    b.currency=$cur, b.date=$date,
                    b.creationDate=$cd, b.isCancelled=$cancelled,
                    b.cancelledDocument=$cancelDoc,
                    b.accountingDocument=$accDoc,
                    b.companyCode=$cc, b.fiscalYear=$fy,
                    b.soldToParty=$stp
                WITH b
                OPTIONAL MATCH (bp:BusinessPartner {id: $stp})
                FOREACH (_ IN CASE WHEN bp IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (b)-[:BILLED_TO]->(bp)
                )
            """, id=r["billingDocument"], type=r.get("billingDocumentType",""),
                 amt=r.get("totalNetAmount","0"),
                 cur=r.get("transactionCurrency",""),
                 date=str(r.get("billingDocumentDate","")),
                 cd=str(r.get("creationDate","")),
                 cancelled=r.get("billingDocumentIsCancelled", False),
                 cancelDoc=r.get("cancelledBillingDocument",""),
                 accDoc=r.get("accountingDocument",""),
                 cc=r.get("companyCode",""), fy=r.get("fiscalYear",""),
                 stp=r.get("soldToParty",""))

        # Billing Cancellations
        for r in load_jsonl("billing_document_cancellations"):
            s.run("""
                MERGE (b:BillingDocument {id: $id})
                SET b.isCancelled=true,
                    b.cancelledDocument=$cancelDoc,
                    b.type=$type, b.amount=toFloat($amt),
                    b.currency=$cur, b.accountingDocument=$accDoc
            """, id=r["billingDocument"],
                 cancelDoc=r.get("cancelledBillingDocument",""),
                 type=r.get("billingDocumentType",""),
                 amt=r.get("totalNetAmount","0"),
                 cur=r.get("transactionCurrency",""),
                 accDoc=r.get("accountingDocument",""))

        # Billing Items
        for r in load_jsonl("billing_document_items"):
            s.run("""
                MERGE (bi:BillingItem {id: $id})
                SET bi.billingDocument=$bId, bi.itemNumber=$itemNo,
                    bi.material=$mat, bi.quantity=toFloat($qty),
                    bi.unit=$unit, bi.amount=toFloat($amt),
                    bi.currency=$cur,
                    bi.referenceDelivery=$refDel,
                    bi.referenceDeliveryItem=$refDelItem
                WITH bi
                MATCH (b:BillingDocument {id: $bId})
                MERGE (b)-[:HAS_ITEM]->(bi)
                WITH bi
                OPTIONAL MATCH (d:Delivery {id: $refDel})
                FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (bi)-[:BASED_ON_DELIVERY]->(d)
                )
                WITH bi
                OPTIONAL MATCH (p:Product {id: $mat})
                FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (bi)-[:FOR_PRODUCT]->(p)
                )
            """, id=r["billingDocument"]+"_"+r["billingDocumentItem"],
                 bId=r["billingDocument"], itemNo=r["billingDocumentItem"],
                 mat=r.get("material",""), qty=r.get("billingQuantity","0"),
                 unit=r.get("billingQuantityUnit",""),
                 amt=r.get("netAmount","0"),
                 cur=r.get("transactionCurrency",""),
                 refDel=r.get("referenceSdDocument",""),
                 refDelItem=r.get("referenceSdDocumentItem",""))

        # Payments
        for r in load_jsonl("payments_accounts_receivable"):
            s.run("""
                MERGE (pay:Payment {id: $id})
                SET pay.amount=toFloat($amt), pay.currency=$cur,
                    pay.clearingDate=$cd, pay.postingDate=$pd,
                    pay.customer=$cust, pay.companyCode=$cc,
                    pay.fiscalYear=$fy,
                    pay.accountingDocument=$accDoc,
                    pay.clearingDocument=$clearDoc
                WITH pay
                OPTIONAL MATCH (b:BillingDocument {accountingDocument: $accDoc})
                FOREACH (_ IN CASE WHEN b IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (pay)-[:CLEARS]->(b)
                )
                WITH pay
                OPTIONAL MATCH (bp:BusinessPartner {id: $cust})
                FOREACH (_ IN CASE WHEN bp IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (pay)-[:PAID_BY]->(bp)
                )
            """, id=r["accountingDocument"]+"_"+str(r["accountingDocumentItem"]),
                 amt=r.get("amountInTransactionCurrency","0"),
                 cur=r.get("transactionCurrency",""),
                 cd=str(r.get("clearingDate","")),
                 pd=str(r.get("postingDate","")),
                 cust=r.get("customer",""),
                 cc=r.get("companyCode",""), fy=r.get("fiscalYear",""),
                 accDoc=r.get("accountingDocument",""),
                 clearDoc=r.get("clearingAccountingDocument",""))

        # Journal Entries
        for r in load_jsonl("journal_entry_items_accounts_receivable"):
            s.run("""
                MERGE (je:JournalEntry {id: $id})
                SET je.amount=toFloat($amt), je.currency=$cur,
                    je.glAccount=$gl, je.postingDate=$pd,
                    je.documentDate=$dd, je.profitCenter=$pc,
                    je.accountingDocument=$accDoc,
                    je.documentType=$docType, je.companyCode=$cc
                WITH je
                OPTIONAL MATCH (b:BillingDocument {id: $refDoc})
                FOREACH (_ IN CASE WHEN b IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (je)-[:RECORDS]->(b)
                )
            """, id=r["accountingDocument"]+"_"+str(r["accountingDocumentItem"]),
                 amt=r.get("amountInTransactionCurrency","0"),
                 cur=r.get("transactionCurrency",""),
                 gl=r.get("glAccount",""),
                 pd=str(r.get("postingDate","")),
                 dd=str(r.get("documentDate","")),
                 pc=r.get("profitCenter",""),
                 accDoc=r.get("accountingDocument",""),
                 docType=r.get("accountingDocumentType",""),
                 cc=r.get("companyCode",""),
                 refDoc=r.get("referenceDocument",""))

    driver.close()
    print("\n✅  Ingestion complete!")
    print("   Verify: MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC")


if __name__ == "__main__":
    ingest()
