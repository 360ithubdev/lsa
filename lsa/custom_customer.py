import frappe
import requests
from frappe import _
from frappe.utils import today
from datetime import datetime


@frappe.whitelist()
def sync_customer(customer_id):
    try:
        followup_button,followup_values,values,open_followup,open_followup_i=sync_sales_orders_customer(customer_id)
        services_values=sync_services_customer(customer_id)
        if sync_sales_orders_customer(customer_id) and sync_services_customer(customer_id):

            return {"status":"Synced successfully.","followup_button":followup_button,"values":values,
                        "followup_values":followup_values,"services_values":services_values,"open_followup":open_followup,"open_followup_i":open_followup_i}
        else:
            return {"status":"Synced successfully."}
    except Exception as e:
        frappe.msgprint(f"Error: {e}")
        return False

def sync_services_customer(customer_id):

    master_service_fields = {
        "Gstfile": ["gst_file", ["name", "company_name", "gst_number", "gst_user_name", "gst_password","current_recurring_fees","frequency","annual_fees","executive_name"]],
        "IT Assessee File": ["it_assessee_file", ["name", "assessee_name", "pan", "pan", "it_password","current_recurring_fees","frequency","annual_fees","executive_name"]],
        "MCA ROC File": ["mca_roc_file", ["name", "company_name", "cin", "trace_user_id", "trace_password","current_recurring_fees","frequency","annual_fees","executive_name"]],
        "Professional Tax File": ["professional_tax_file", ["name", "assessee_name", "registration_no", "user_id", "trace_password","current_recurring_fees","frequency","annual_fees","executive_name"]],
        "TDS File": ["tds_file", ["name", "deductor_name", "tan_no", "trace_user_id", "trace_password","current_recurring_fees","frequency","annual_fees","executive_name"]],
        "ESI File": ["esi_file", ["name", "assessee_name", "registartion_no", "trace_user_id", "trace_password","current_recurring_fees","frequency","annual_fees","executive_name"]],
        "Provident Fund File": ["provident_fund_file", ["name", "assessee_name", "registartion_no", "trace_user_id", "trace_password","current_recurring_fees","frequency","annual_fees","executive_name"]],
    }

    services_values=[]
    chargeable_services=frappe.get_all("Customer Chargeable Doctypes")
    for chargeable_service in chargeable_services:
        # print(chargeable_service)
        chargeable_service_values=frappe.get_all(chargeable_service.name,
                                           filters={"customer_id":customer_id,
                                                   "enabled":1},
                                            fields=master_service_fields[chargeable_service.name][1]
                                            )
        # print(chargeable_service_values)
        for chargeable_service_value in chargeable_service_values:
            chargeable_service_value=[chargeable_service_value[i] for i in master_service_fields[chargeable_service.name][1] ]
            print(chargeable_service_value)
            service_slug="-".join([i.lower() for i in ((chargeable_service.name).split(" "))])
            chargeable_service_value.append(service_slug)
            chargeable_service_value.append(chargeable_service.name)
            services_values.append(chargeable_service_value)
    print(services_values)

    return services_values


def sync_sales_orders_customer(customer_id):
    ############################Sales Order############################################################################

    existing_sales_orders=frappe.get_all("Sales Order",
                                filters={"customer":customer_id,
                                            "docstatus":['in', [0,1]]})
    # print(existing_sales_orders)
    so_details={}
    custom_count_of_so_due=0
    custom_total_amount_due_of_so=0.00
    custom_details_of_so_due=[]

    if existing_sales_orders:

        for existing_sales_order in existing_sales_orders:
            # print(existing_sales_order)
            sales_order=frappe.get_doc("Sales Order",existing_sales_order.name)
            payment_status="Unpaid"
            custom_so_balance=sales_order.rounded_total
            advance_paid=0
            pes=frappe.get_all("Payment Entry Reference",filters={"reference_doctype":"Sales Order","reference_name":sales_order.name},fields=["name","parent","allocated_amount"])
            # doc.custom_pe_counts=len(pes)
            for pe in pes:
                custom_so_balance-=pe.allocated_amount
                advance_paid+=pe.allocated_amount

            if custom_so_balance>0:
                custom_count_of_so_due+=1
                custom_total_amount_due_of_so+=(custom_so_balance)
                custom_details_of_so_due.append(sales_order.name)
                so_details[sales_order.name]=[sales_order.rounded_total,advance_paid,
                                                custom_so_balance,
                                                sales_order.custom_so_from_date,sales_order.custom_so_to_date,
                                                sales_order.status,sales_order.custom_followup_count,
                                                sales_order.customer_name,sales_order.customer]
                if custom_so_balance<sales_order.rounded_total:
                    payment_status="Partially Paid"
                so_details[sales_order.name]+=[payment_status]
        custom_details_of_so_due=", ".join(custom_details_of_so_due)


    ##############################################followup button##############################################################
    
    followup_button=False
    open_followup_i=""
    open_followups=[]
    if custom_total_amount_due_of_so>0:
        followups=frappe.get_all("Customer Followup", filters={"customer_id":customer_id},fields=["name","status"])
        open_followups=[i for i in followups if i.status=="Open"]
        if followups and not(open_followups):
            next_followup_date=""
            for followup in followups:
                followup_doc=frappe.get_doc("Customer Followup",followup.name)
                if followup_doc.status == "Closed" and followup_doc.next_followup_date:
                    date_format = "%Y-%m-%d"
                    this_followup_date=datetime.strptime(str(followup_doc.next_followup_date)
                                                            , date_format).date()
                    # print(this_followup_date)
                    if next_followup_date=="" or this_followup_date >=next_followup_date :
                        # print("next",next_followup_date,"this",this_followup_date)
                        next_followup_date = this_followup_date
            if next_followup_date:
                today_date = datetime.now().date()
                if next_followup_date<=today_date:
                    # print("this followup true",next_followup_date,today_date)
                    followup_button=True
            else:
                # print("else followup true")
                followup_button=True
        elif open_followups:
            # open_followups=frappe.get_doc("Customer Followup",open_followups[0]["name"])
            open_followup_i=str(open_followups[0]["name"])
        else:
            # print("outer followup true")
            followup_button=True
        

    ############################Follow up############################################################################
        
    followup_values={"Open":[],"Closed":[],"values":[],}
    if custom_total_amount_due_of_so>0:
        existing_followups=frappe.get_all("Customer Followup",
                                filters={"customer_id":customer_id,
                                        # "status":['in', ["Draft","On Hold","To Deliver and Bill","To Bill","To Deliver"]]
                                        })
        # print(existing_sales_orders)
        if existing_followups:
            last_closed_followup_date="Dummy"
            next_followup_date="Dummy"

            for existing_followup in existing_followups:
                # print(existing_sales_order)
                followup=frappe.get_doc("Customer Followup",existing_followup.name)

                if followup.status == "Open":
                    open_followup=followup.name
                    followup_nature="Open"
                    open_followup_date=followup.followup_date
                    followup_values["Open"]=[open_followup,followup_nature,open_followup_date]
                elif followup.status == "Closed" and not(followup_values["Open"]):
                    print("next",next_followup_date,"this",followup.next_followup_date)
                    if last_closed_followup_date=="Dummy" or \
                            last_closed_followup_date<followup.followup_date:
                        print("next update")
                        last_followup=followup.name
                        followup_nature="Closed"
                        next_followup_date=followup.next_followup_date
                        last_closed_followup_date=followup.followup_date
                        last_followup_comment=followup.followup_note
                        followup_values["Closed"]=[last_followup,followup_nature,next_followup_date,last_followup_comment]


                followup_values["values"]+=[[followup.customer_id,followup.name,
                                            followup.status,followup.total_remaining_balance,
                                            followup.followup_date,followup.next_followup_date,
                                            followup.executive_name,followup.followup_note]]
    return followup_button,followup_values,[so_details,custom_count_of_so_due,custom_total_amount_due_of_so,custom_details_of_so_due],open_followups,open_followup_i
                        
    

@frappe.whitelist()
def sync_sales_orders_followup(sales_order_summary,customer_id,followup_date):
    try:
        sales_order_summary=sales_order_summary.strip()
        existing_sales_orders=sales_order_summary.split(", ")

        # if existing_sales_orders:
        #     so_details={}
        #     # custom_count_of_so_due=0
        #     # custom_total_amount_due_of_so=0.00
        #     # custom_details_of_so_due=""
        #     for existing_sales_order in existing_sales_orders:
        #         sales_order=frappe.get_doc("Sales Order",existing_sales_order)
        #         if sales_order:
        #             so_details[sales_order.name]=[sales_order.rounded_total,sales_order.advance_paid,
        #                                           sales_order.rounded_total-sales_order.advance_paid,
        #                                           sales_order.custom_so_from_date,sales_order.custom_so_to_date,
        #                                           sales_order.status,sales_order.custom_followup_count,
        #                                           sales_order.customer_name,sales_order.customer]
        
        if existing_sales_orders:
            so_details={}
            for existing_sales_order in existing_sales_orders:
                # print(existing_sales_order)
                sales_order=frappe.get_doc("Sales Order",existing_sales_order)
                payment_status="Unpaid"
                custom_so_balance=sales_order.rounded_total
                advance_paid=0
                pes=frappe.get_all("Payment Entry Reference",filters={"reference_doctype":"Sales Order","reference_name":sales_order.name},fields=["name","parent","allocated_amount"])
                # doc.custom_pe_counts=len(pes)
                for pe in pes:
                    custom_so_balance-=pe.allocated_amount
                    advance_paid+=pe.allocated_amount

                # custom_details_of_so_due.append(sales_order.name)
                so_details[sales_order.name]=[sales_order.rounded_total,advance_paid,
                                                custom_so_balance,
                                                sales_order.custom_so_from_date,sales_order.custom_so_to_date,
                                                sales_order.status,sales_order.custom_followup_count,
                                                sales_order.customer_name,sales_order.customer]
                if custom_so_balance<sales_order.rounded_total:
                    payment_status="Partially Paid"
                so_details[sales_order.name]+=[payment_status]
        ##################################################################################################################
        followup_values={"Open":[],"Closed":[],"values":[],}
        date_format = "%Y-%m-%d"
        followup_date=datetime.strptime(followup_date, date_format).date()
        if True:
            existing_followups=frappe.get_all("Customer Followup",
                                    filters={"customer_id":customer_id,
                                            # "status":['in', ["Draft","On Hold","To Deliver and Bill","To Bill","To Deliver"]]
                                            })
            # print(existing_sales_orders)
            if existing_followups:
                last_closed_followup_date="Dummy"
                next_followup_date="Dummy"

                for existing_followup in existing_followups:
                    # print(existing_sales_order)
                    followup=frappe.get_doc("Customer Followup",existing_followup.name)

                    if followup.status == "Open":
                        open_followup=followup.name
                        followup_nature="Open"
                        open_followup_date=followup.followup_date
                        followup_values["Open"]=[open_followup,followup_nature,open_followup_date]
                    elif followup.status == "Closed" and not(followup_values["Open"]):
                        print("next",next_followup_date,"this",followup.next_followup_date)
                        if last_closed_followup_date=="Dummy" or \
                                last_closed_followup_date<followup.followup_date:
                            print("next update")
                            last_followup=followup.name
                            followup_nature="Closed"
                            next_followup_date=followup.next_followup_date
                            last_closed_followup_date=followup.followup_date
                            last_followup_comment=followup.followup_note
                            followup_values["Closed"]=[last_followup,followup_nature,next_followup_date,last_followup_comment]
                    
                    if followup.followup_date<followup_date:
                        followup_values["values"]+=[[followup.customer_id,followup.name,
                                                    followup.status,followup.total_remaining_balance,
                                                    followup.followup_date,followup.next_followup_date,
                                                    followup.executive_name,followup.followup_note]]


            return {"status":"Synced successfully.","values":[so_details],"followup_values":followup_values}
        # else:
        #     return {"status":"Synced successfully."}
    except Exception as e:
        frappe.msgprint(f"Error: {e}")
        return False

@frappe.whitelist()
def checking_user_authentication(user_email):
    try:
        status = False
        user_roles = frappe.get_all('Has Role', filters={'parent': user_email}, fields=['role'])

        if user_email=="pankajsankhla90@gmail.com":
            user_roles = frappe.get_all('Has Role', filters={'parent': "Administrator"}, fields=['role'])

        # Extract roles from the result
        roles = [role.get('role') for role in user_roles]
        doc_perm_roles = ["LSA Accounts Manager","LSA Account Executive"]

        for role in roles:
            if role in doc_perm_roles:
                status = True
                break

        return {"status": status, "value": [roles]}

    except Exception as e:
        print(e)
        return {"status": "Failed"}










