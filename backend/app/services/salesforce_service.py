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
        """Establish connection to Salesforce"""
        try:
            self.sf = Salesforce(
                username=settings.SALESFORCE_USERNAME,
                password=settings.SALESFORCE_PASSWORD,
                security_token=settings.SALESFORCE_SECURITY_TOKEN,
                domain=settings.SALESFORCE_DOMAIN
            )
        except Exception as e:
            print(f"Failed to connect to Salesforce: {e}")
            # For PoC, we'll continue without connection
            self.sf = None
    
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


# Singleton instance
salesforce_service = SalesforceService()
