"""
Salesforce integration service
"""
import json
import ssl
import os
from typing import List, Dict, Any, Optional
from app.core.config import settings

# Disable SSL verification if configured (for corporate proxy environments)
if not settings.SALESFORCE_VERIFY_SSL:
    # Method 1: Set environment variables for requests/urllib3
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    
    # Method 2: Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Method 3: Monkey-patch ssl to use unverified context
    ssl._create_default_https_context = ssl._create_unverified_context
    
    print("⚠️ SSL verification globally disabled for Salesforce connections")

from simple_salesforce import Salesforce
from app.models.schemas import CaseData, RelatedObjectData


class SalesforceService:
    """Service for interacting with Salesforce API"""
    
    def __init__(self):
        """Initialize Salesforce connection"""
        self.sf: Optional[Salesforce] = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Salesforce using OAuth 2.0 or Username/Password"""
        try:
            # Determine which authentication method to use
            has_oauth = settings.SALESFORCE_CLIENT_ID and settings.SALESFORCE_CLIENT_SECRET
            has_username_pwd = settings.SALESFORCE_USERNAME and settings.SALESFORCE_PASSWORD
            
            if has_oauth:
                print("🔐 Attempting Salesforce connection using OAuth 2.0...")
                self._connect_oauth()
            elif has_username_pwd:
                print("🔐 Attempting Salesforce connection using Username/Password...")
                self._connect_username_password()
            else:
                print("❌ No Salesforce credentials configured. Please set either:")
                print("   - OAuth: SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET")
                print("   - Username/Password: SALESFORCE_USERNAME, SALESFORCE_PASSWORD, and SALESFORCE_SECURITY_TOKEN")
                self.sf = None
        except Exception as e:
            print(f"❌ Failed to connect to Salesforce: {e}")
            print(f"   Error type: {type(e).__name__}")
            # For PoC, we'll continue without connection
            self.sf = None
    
    def _connect_oauth(self):
        """Connect to Salesforce using OAuth 2.0 Client Credentials Flow"""
        import requests
        
        # Construct the token endpoint URL
        if settings.SALESFORCE_DOMAIN in ['login', 'test']:
            base_url = f"https://{settings.SALESFORCE_DOMAIN}.salesforce.com"
        else:
            # Custom domain (e.g., mycompany.my.salesforce.com)
            base_url = f"https://{settings.SALESFORCE_DOMAIN}.salesforce.com"
        
        token_url = f"{base_url}/services/oauth2/token"
        
        # If we have username/password along with client credentials, use password grant
        if settings.SALESFORCE_USERNAME and settings.SALESFORCE_PASSWORD:
            # OAuth 2.0 Password Grant (more common for service accounts)
            combined_password = settings.SALESFORCE_PASSWORD + settings.SALESFORCE_SECURITY_TOKEN
            payload = {
                'grant_type': 'password',
                'client_id': settings.SALESFORCE_CLIENT_ID,
                'client_secret': settings.SALESFORCE_CLIENT_SECRET,
                'username': settings.SALESFORCE_USERNAME,
                'password': combined_password
            }
            print(f"   Using OAuth 2.0 Password Grant to {token_url}")
            # Debug: Show credential info (masked) to help troubleshoot
            print(f"   📋 Credentials being used:")
            print(f"      Username: {settings.SALESFORCE_USERNAME}")
            print(f"      Client ID: {settings.SALESFORCE_CLIENT_ID[:10]}...{settings.SALESFORCE_CLIENT_ID[-5:]}")
            print(f"      Client Secret length: {len(settings.SALESFORCE_CLIENT_SECRET)} chars")
            print(f"      Password length: {len(settings.SALESFORCE_PASSWORD)} chars")
            print(f"      Security Token length: {len(settings.SALESFORCE_SECURITY_TOKEN)} chars")
            print(f"      Combined password+token length: {len(combined_password)} chars")
        else:
            # OAuth 2.0 Client Credentials Grant (requires JWT Bearer flow setup in SF)
            # Note: This requires additional setup in Salesforce with a Connected App
            payload = {
                'grant_type': 'client_credentials',
                'client_id': settings.SALESFORCE_CLIENT_ID,
                'client_secret': settings.SALESFORCE_CLIENT_SECRET
            }
            print(f"   Using OAuth 2.0 Client Credentials Grant to {token_url}")
        
        try:
            # Use SSL verification setting (disable for corporate proxy environments)
            verify_ssl = settings.SALESFORCE_VERIFY_SSL
            if not verify_ssl:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                print("   ⚠️ SSL verification disabled")
            
            response = requests.post(token_url, data=payload, timeout=10, verify=verify_ssl)
            response.raise_for_status()
            
            oauth_response = response.json()
            
            # Extract access token and instance URL
            access_token = oauth_response['access_token']
            instance_url = oauth_response['instance_url']
            
            print(f"✅ OAuth token obtained successfully")
            print(f"   Instance URL: {instance_url}")
            
            # Create Salesforce connection with the access token
            self.sf = Salesforce(
                instance_url=instance_url,
                session_id=access_token
            )
            
        except requests.exceptions.HTTPError as e:
            error_details = ""
            try:
                error_details = e.response.json()
                print(f"❌ OAuth authentication failed: {error_details}")
            except:
                print(f"❌ OAuth authentication failed: {e}")
            raise Exception(f"OAuth authentication failed: {error_details or str(e)}")
        except Exception as e:
            print(f"❌ OAuth connection error: {e}")
            raise
    
    def _connect_username_password(self):
        """Connect to Salesforce using Username/Password/Security Token"""
        import requests
        
        # For custom domains, simple-salesforce expects just the domain name
        # For example: 'royalcanin-us--rcdev.sandbox.my' (not full URL)
        # The library constructs https://[domain].salesforce.com internally
        # Standard domains: 'login' or 'test'
        
        print(f"   Domain: {settings.SALESFORCE_DOMAIN}")
        print(f"   Username: {settings.SALESFORCE_USERNAME}")
        
        # Create session with SSL verification setting
        session = requests.Session()
        session.verify = settings.SALESFORCE_VERIFY_SSL
        
        if not settings.SALESFORCE_VERIFY_SSL:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            print("   ⚠️ SSL verification disabled")
        
        self.sf = Salesforce(
            username=settings.SALESFORCE_USERNAME,
            password=settings.SALESFORCE_PASSWORD,
            security_token=settings.SALESFORCE_SECURITY_TOKEN,
            domain=settings.SALESFORCE_DOMAIN,
            session=session
        )
        
        print(f"✅ Connected successfully")
        print(f"   Instance: {self.sf.sf_instance}")
    
    def check_connection(self) -> Dict[str, Any]:
        """
        Check Salesforce connection health
        
        Returns:
            Dictionary with connection status and details
        """
        if not self.sf:
            return {
                "connected": False,
                "status": "disconnected",
                "message": "Salesforce connection not established. Please verify credentials.",
                "error": "Connection object is None"
            }
        
        try:
            # Test connection with a simple query
            result = self.sf.query("SELECT Id FROM User LIMIT 1")
            
            return {
                "connected": True,
                "status": "connected",
                "message": "Salesforce connection is healthy",
                "details": {
                    "instance_url": self.sf.sf_instance,
                    "api_version": self.sf.sf_version,
                    "session_active": self.sf.session_id is not None,
                    "query_test": "passed"
                }
            }
        except Exception as e:
            return {
                "connected": False,
                "status": "error",
                "message": f"Connection exists but API call failed: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def get_case_by_id(self, case_id: str) -> Optional[CaseData]:
        """
        Retrieve case details from Salesforce
        
        Args:
            case_id: Salesforce Case ID
        
        Returns:
            CaseData object or None if not found
        """
        if not self.sf:
            # Return mock data for PoC
            return self._get_mock_case(case_id)
        
        try:
            case = self.sf.Case.get(case_id)
            return CaseData(
                case_id=case['Id'],
                case_number=case.get('CaseNumber', ''),
                subject=case.get('Subject', ''),
                description=case.get('Description', ''),
                priority=case.get('Priority', 'Medium'),
                status=case.get('Status', 'New'),
                is_closed=case.get('IsClosed', False),
                created_date=case.get('CreatedDate', ''),
                account_id=case.get('AccountId'),
                contact_id=case.get('ContactId')
            )
        except Exception as e:
            print(f"Error fetching case {case_id}: {e}")
            return None
    
    def get_case_by_number(self, case_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve case details with account and contact using CaseNumber
        Uses a single SOQL query to fetch all essential data.
        
        Args:
            case_number: Salesforce Case Number (user-visible, e.g., '00001234')
        
        Returns:
            Dictionary with case, account, and contact data or None if not found
        """
        if not self.sf:
            print("❌ Salesforce not connected - cannot fetch case by number")
            return None
        
        try:
            # SOQL query with essential fields for the copilot
            soql_query = f"""
                SELECT 
                    Id, CaseNumber, Subject, Description, Priority, Status, IsClosed,
                    ClosedDate, CreatedDate, Origin, Type, Reason,
                    AccountId, ContactId, OwnerId,
                    Owner.Id, Owner.Name, Owner.Email,
                    Customer_Type__c, Customer_Sentiment__c, Issue_Type__c, Specific_Issue__c,
                    Resolution__c, Resolution_Comments__c,
                    
                    Account_Reference__r.Id, Account_Reference__r.Name,
                    Account_Reference__r.gii__Account__c,
                    Account_Reference__r.gii__BalanceAmount__c,
                    Account_Reference__r.gii__CreditLimit__c,
                    Account_Reference__r.gii__PaymentTerms__c,
                    Account_Reference__r.Ship_To_Customer_No__c,
                    
                    Contact.Id, Contact.Name, Contact.FirstName, Contact.LastName,
                    Contact.Email, Contact.Phone, Contact.MobilePhone,
                    Contact.Title, Contact.Department,
                    Contact.MailingCity, Contact.MailingState, Contact.MailingCountry,
                    Contact.Customer_Type__c, Contact.Account_Ship_To_Customer_No__c
                    
                FROM Case 
                WHERE CaseNumber = '{case_number}'
                LIMIT 1
            """
            
            result = self.sf.query(soql_query)
            
            if result['totalSize'] == 0:
                print(f"❌ Case with number {case_number} not found")
                return None
            
            case_record = result['records'][0]
            
            # Check if case is closed
            is_closed = case_record.get('Status', 'Closed')
            
            # Extract case data
            case_data = {
                'case_id': case_record.get('Id'),
                'case_number': case_record.get('CaseNumber'),
                'subject': case_record.get('Subject', ''),
                'description': case_record.get('Description', ''),
                'priority': case_record.get('Priority', 'Medium'),
                'status': case_record.get('Status', 'New'),
                'is_closed': is_closed,
                'closed_date': case_record.get('ClosedDate'),
                'created_date': case_record.get('CreatedDate', ''),
                'origin': case_record.get('Origin'),
                'type': case_record.get('Type'),
                'reason': case_record.get('Reason'),
                'customer_type': case_record.get('Customer_Type__c'),
                'customer_sentiment': case_record.get('Customer_Sentiment__c'),
                'issue_type': case_record.get('Issue_Type__c'),
                'specific_issue': case_record.get('Specific_Issue__c'),
                'resolution': case_record.get('Resolution__c'),
                'resolution_comments': case_record.get('Resolution_Comments__c'),
                'account_id': case_record.get('AccountId'),
                'contact_id': case_record.get('ContactId')
            }
            
            # Extract account reference data
            account_ref = case_record.get('Account_Reference__r')
            account_data = None
            if account_ref:
                account_data = {
                    'id': account_ref.get('Id'),
                    'name': account_ref.get('Name'),
                    'account': account_ref.get('gii__Account__c'),
                    'balance_amount': account_ref.get('gii__BalanceAmount__c'),
                    'credit_limit': account_ref.get('gii__CreditLimit__c'),
                    'payment_terms': account_ref.get('gii__PaymentTerms__c'),
                    'ship_to_customer_no': account_ref.get('Ship_To_Customer_No__c')
                }
            
            # Extract contact data
            contact = case_record.get('Contact')
            contact_data = None
            if contact:
                contact_data = {
                    'id': contact.get('Id'),
                    'name': contact.get('Name'),
                    'first_name': contact.get('FirstName'),
                    'last_name': contact.get('LastName'),
                    'email': contact.get('Email'),
                    'phone': contact.get('Phone'),
                    'mobile_phone': contact.get('MobilePhone'),
                    'title': contact.get('Title'),
                    'department': contact.get('Department'),
                    'mailing_city': contact.get('MailingCity'),
                    'mailing_state': contact.get('MailingState'),
                    'mailing_country': contact.get('MailingCountry'),
                    'customer_type': contact.get('Customer_Type__c'),
                    'ship_to_customer_no': contact.get('Account_Ship_To_Customer_No__c')
                }
            
            # Extract owner (agent) data
            owner = case_record.get('Owner')
            owner_data = None
            if owner:
                owner_data = {
                    'id': owner.get('Id'),
                    'name': owner.get('Name'),
                    'email': owner.get('Email')
                }
            
            return {
                'case': case_data,
                'account': account_data,
                'contact': contact_data,
                'owner': owner_data,
                'has_account': account_data is not None,
                'has_contact': contact_data is not None,
                'has_owner': owner_data is not None
            }
            
        except Exception as e:
            print(f"❌ Error fetching case by number {case_number}: {e}")
            return None
    
    def get_active_users(self, limit: int = 3, exclude_user_id: str = None) -> List[Dict[str, Any]]:
        """
        Get active standard users from Salesforce
        
        Args:
            limit: Maximum number of users to return (default 3)
            exclude_user_id: User ID to exclude (e.g., case owner)
        
        Returns:
            List of user dictionaries with id, name, email
        """
        if not self.sf:
            print("❌ Salesforce not connected - cannot fetch users")
            return []
        
        try:
            # Build exclusion clause
            exclude_clause = ""
            if exclude_user_id:
                exclude_clause = f"AND Id != '{exclude_user_id}'"
            
            # Query active standard users
            soql_query = f"""
                SELECT Id, Name, Email
                FROM User
                WHERE IsActive = true 
                AND UserType = 'Standard'
                {exclude_clause}
                ORDER BY Name
                LIMIT {limit}
            """
            
            result = self.sf.query(soql_query)
            
            users = []
            for record in result.get('records', []):
                users.append({
                    'id': record.get('Id'),
                    'name': record.get('Name'),
                    'email': record.get('Email')
                })
            
            print(f"✅ Found {len(users)} active users")
            return users
            
        except Exception as e:
            print(f"❌ Error fetching active users: {e}")
            return []
    
    def get_related_objects(self, case_id: str) -> List[RelatedObjectData]:
        """
        Retrieve related objects data for a case
        
        Args:
            case_id: Salesforce Case ID
        
        Returns:
            List of RelatedObjectData objects
        """
        if not self.sf:
            # Return mock data for PoC
            return self._get_mock_related_objects(case_id)
        
        related_data = []
        
        # Load configuration
        with open('app/data/related_objects_config.json', 'r') as f:
            config = json.load(f)
        
        case = self.get_case_by_id(case_id)
        if not case:
            return related_data
        
        for obj_config in config['case_related_objects']['objects']:
            try:
                records = self._fetch_related_records(
                    case,
                    obj_config['name'],
                    obj_config['fields'],
                    obj_config.get('relationship')
                )
                
                if records:
                    related_data.append(RelatedObjectData(
                        object_name=obj_config['name'],
                        records=records
                    ))
            except Exception as e:
                print(f"Error fetching {obj_config['name']}: {e}")
        
        return related_data
    
    def _fetch_related_records(
        self,
        case: CaseData,
        object_name: str,
        fields: List[str],
        relationship: str
    ) -> List[Dict[str, Any]]:
        """Fetch related records from Salesforce"""
        # Implementation would use SOQL queries
        # For PoC, return empty list
        return []
    
    def _get_mock_case(self, case_id: str) -> CaseData:
        """Return mock case data for PoC"""
        return CaseData(
            case_id=case_id,
            subject="Customer unable to access premium features",
            description="Customer reports that after upgrading to premium plan, they still cannot access advanced analytics dashboard. Error message: 'Access Denied - Contact Support'",
            priority="High",
            status="New",
            created_date="2025-11-25T10:30:00Z",
            account_id="001XX000003DHH0",
            contact_id="003XX000001234"
        )
    
    def _get_mock_related_objects(self, case_id: str) -> List[RelatedObjectData]:
        """Return mock related objects data for PoC"""
        return [
            RelatedObjectData(
                object_name="Account",
                records=[{
                    "Id": "001XX000003DHH0",
                    "Name": "TechVision Solutions",
                    "Industry": "Technology",
                    "Type": "Customer - Direct",
                    "Phone": "+1-555-0123",
                    "BillingCity": "San Francisco",
                    "BillingCountry": "USA"
                }]
            ),
            RelatedObjectData(
                object_name="Contact",
                records=[{
                    "Id": "003XX000001234",
                    "Name": "Jennifer Martinez",
                    "Email": "jennifer.martinez@techvision.com",
                    "Phone": "+1-555-0124",
                    "Title": "Product Manager",
                    "Department": "Product"
                }]
            ),
            RelatedObjectData(
                object_name="CaseComment",
                records=[
                    {
                        "Id": "00aXX000001111",
                        "CommentBody": "Customer upgraded to Premium plan on 2025-11-24",
                        "CreatedDate": "2025-11-25T09:00:00Z",
                        "IsPublished": True
                    },
                    {
                        "Id": "00aXX000001112",
                        "CommentBody": "Verified payment processed successfully. Account status shows Premium.",
                        "CreatedDate": "2025-11-25T09:15:00Z",
                        "IsPublished": False
                    }
                ]
            ),
            RelatedObjectData(
                object_name="EmailMessage",
                records=[{
                    "Id": "02sXX000001ABC",
                    "Subject": "Re: Premium Plan Upgrade",
                    "TextBody": "Thank you for upgrading! You should now have access to all premium features.",
                    "FromAddress": "support@company.com",
                    "ToAddress": "jennifer.martinez@techvision.com",
                    "MessageDate": "2025-11-24T16:30:00Z",
                    "Status": "Sent"
                }]
            )
        ]
    
    def save_case_summary(self, case_id: str, summary: str, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Save case summary to a Salesforce custom object
        
        Args:
            case_id: Salesforce Case ID
            summary: The AI-generated summary text
            additional_data: Optional additional fields to save
        
        Returns:
            Dictionary with status and record ID
        """
        if not self.sf:
            # Mock response for when not connected
            print("⚠️ Salesforce not connected - returning mock save response")
            return {
                "success": True,
                "record_id": f"a00MOCK{case_id[-5:]}",
                "message": "Summary saved (mock mode)",
                "case_id": case_id
            }
        
        try:
            # Get custom object configuration
            object_name = settings.SUMMARY_OBJECT_API_NAME
            summary_field = settings.SUMMARY_FIELD_NAME
            case_field = settings.CASE_ID_FIELD_NAME
            
            # Build the record data
            record_data = {
                case_field: case_id,
                summary_field: summary
            }
            
            # Add any additional data
            if additional_data:
                record_data.update(additional_data)
            
            # Check if a summary already exists for this case
            existing = self.sf.query(
                f"SELECT Id FROM {object_name} WHERE {case_field} = '{case_id}' LIMIT 1"
            )
            
            if existing['totalSize'] > 0:
                # Update existing record
                existing_id = existing['records'][0]['Id']
                getattr(self.sf, object_name).update(existing_id, record_data)
                print(f"✅ Updated existing summary record: {existing_id}")
                return {
                    "success": True,
                    "record_id": existing_id,
                    "message": "Summary updated successfully",
                    "case_id": case_id,
                    "action": "update"
                }
            else:
                # Create new record
                result = getattr(self.sf, object_name).create(record_data)
                record_id = result['id']
                print(f"✅ Created new summary record: {record_id}")
                return {
                    "success": True,
                    "record_id": record_id,
                    "message": "Summary saved successfully",
                    "case_id": case_id,
                    "action": "create"
                }
                
        except Exception as e:
            print(f"❌ Error saving summary: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save summary: {str(e)}",
                "case_id": case_id
            }


# Singleton instance
salesforce_service = SalesforceService()
