"""
Salesforce integration service
"""
import json
from typing import List, Dict, Any, Optional
from simple_salesforce import Salesforce
from app.core.config import settings
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
            response = requests.post(token_url, data=payload, timeout=10)
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
        # For custom domains, simple-salesforce expects just the domain name
        # For example: 'royalcanin-us--rcdev.sandbox.my' (not full URL)
        # The library constructs https://[domain].salesforce.com internally
        # Standard domains: 'login' or 'test'
        
        print(f"   Domain: {settings.SALESFORCE_DOMAIN}")
        print(f"   Username: {settings.SALESFORCE_USERNAME}")
        
        self.sf = Salesforce(
            username=settings.SALESFORCE_USERNAME,
            password=settings.SALESFORCE_PASSWORD,
            security_token=settings.SALESFORCE_SECURITY_TOKEN,
            domain=settings.SALESFORCE_DOMAIN
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
                subject=case.get('Subject', ''),
                description=case.get('Description', ''),
                priority=case.get('Priority', 'Medium'),
                status=case.get('Status', 'New'),
                created_date=case.get('CreatedDate', ''),
                account_id=case.get('AccountId'),
                contact_id=case.get('ContactId')
            )
        except Exception as e:
            print(f"Error fetching case {case_id}: {e}")
            return None
    
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
