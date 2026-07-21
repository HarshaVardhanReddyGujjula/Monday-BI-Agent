import requests
from typing import Dict, List, Any, Optional
from config import (
    MONDAY_API_KEY,
    MONDAY_API_URL,
    MONDAY_BOARD_ID_DEALS,
    MONDAY_BOARD_ID_WORK_ORDERS,
    logger
)

class MondayClient:
    """
    Production-ready GraphQL client for monday.com.
    Handles cursor-based pagination, network errors, timeouts, and structured data parsing.
    """
    
    def __init__(self):
        self.api_key = MONDAY_API_KEY
        self.api_url = MONDAY_API_URL
        self.headers = {
            "Authorization": self.api_key if self.api_key else "",
            "Content-Type": "application/json",
            "API-Version": "2023-10"  # Set to stable monday.com API version
        }
        self.timeout = 15  # seconds
        
    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a GraphQL query against the monday.com API.
        Handles API token verification, network failures, timeouts, and GraphQL errors.
        """
        if not self.api_key:
            raise ValueError(
                "MONDAY_API_KEY is not configured. Please set MONDAY_API_KEY in your .env file."
            )
            
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        try:
            logger.debug(f"Sending GraphQL query to monday.com. Query snippet: {query[:100]}...")
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=self.headers, 
                timeout=self.timeout
            )
            
            # Handle standard HTTP error codes
            if response.status_code == 401:
                logger.error("Authentication failed: Invalid Monday API token.")
                raise PermissionError("Unauthorized: Invalid Monday.com API Token.")
            elif response.status_code == 403:
                logger.error("Forbidden: Access denied to monday.com board or resources.")
                raise PermissionError("Forbidden: Access denied to monday.com board.")
            
            response.raise_for_status()
            result = response.json()
            
            # Check for GraphQL errors returned inside a 200 OK response
            if "errors" in result:
                err_msg = result["errors"][0].get("message", "Unknown GraphQL error")
                logger.error(f"Monday.com API returned query errors: {result['errors']}")
                raise RuntimeError(f"Monday.com API Error: {err_msg}")
                
            return result
            
        except requests.exceptions.Timeout:
            logger.error("Network timeout reached while connecting to monday.com API.")
            raise TimeoutError("Connection to monday.com timed out.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network transport error encountered: {str(e)}")
            raise ConnectionError(f"Failed to connect to monday.com: {str(e)}")

    def _fetch_all_items(self, board_id: str) -> List[Dict[str, Any]]:
        """
        Generic helper method that retrieves all items from a specified board.
        Handles cursor-based pagination seamlessly.
        """
        if not board_id:
            logger.error("Board ID is empty or not provided.")
            raise ValueError("Board ID is required to fetch items.")
            
        logger.info(f"Initiating full fetch for monday.com board ID: {board_id}")
        
        # Initial query to fetch board column metadata and the first page of items
        initial_query = """
        query ($boardId: [ID!]) {
          boards(ids: $boardId) {
            name
            columns {
              id
              title
              type
            }
            items_page(limit: 100) {
              cursor
              items {
                id
                name
                column_values {
                  id
                  text
                  value
                }
              }
            }
          }
        }
        """
        
        try:
            # Execute initial query
            response_data = self.execute_query(initial_query, variables={"boardId": [str(board_id)]})
            
            boards = response_data.get("data", {}).get("boards", [])
            if not boards:
                logger.warning(f"No board found with ID: {board_id}")
                return []
                
            board_data = boards[0]
            board_name = board_data.get("name", "Unknown Board")
            columns = board_data.get("columns", [])
            items_page = board_data.get("items_page", {})
            
            # Map column IDs to Column Titles for intuitive lookup
            col_map = {col["id"]: col["title"] for col in columns}
            logger.info(f"Connected to board '{board_name}'. Columns mapped: {len(col_map)}")
            
            raw_items = items_page.get("items", [])
            cursor = items_page.get("cursor")
            
            parsed_items = [self._parse_item(item, col_map) for item in raw_items]
            
            # Pagination loop: Fetch subsequent pages using cursors
            page_count = 1
            while cursor:
                logger.info(f"Fetching subsequent page {page_count + 1} using pagination cursor...")
                pagination_query = """
                query ($cursor: String!) {
                  next_items_page(cursor: $cursor, limit: 100) {
                    cursor
                    items {
                      id
                      name
                      column_values {
                        id
                        text
                        value
                      }
                    }
                  }
                }
                """
                page_data = self.execute_query(pagination_query, variables={"cursor": cursor})
                next_page = page_data.get("data", {}).get("next_items_page", {})
                
                new_items = next_page.get("items", [])
                parsed_items.extend([self._parse_item(item, col_map) for item in new_items])
                
                cursor = next_page.get("cursor")
                page_count += 1
                
            logger.info(f"Successfully loaded {len(parsed_items)} items across {page_count} page(s) from board '{board_name}'.")
            return parsed_items
            
        except Exception as e:
            logger.error(f"Error occurred while pulling board {board_id} items: {str(e)}")
            raise

    def _parse_item(self, item: Dict[str, Any], col_map: Dict[str, str]) -> Dict[str, Any]:
        """
        Parses a single GraphQL item into a clean Python dictionary.
        Maps column IDs back to user-friendly column titles.
        """
        parsed = {
            "Item ID": item.get("id"),
            "Name": item.get("name")
        }
        
        for col_val in item.get("column_values", []):
            col_id = col_val.get("id")
            # Resolve the column title, fall back to column ID if missing
            col_title = col_map.get(col_id, col_id)
            col_text = col_val.get("text")
            
            # Save clean, stripped values
            parsed[col_title] = col_text.strip() if col_text else ""
            
        return parsed

    def get_deals(self) -> List[Dict[str, Any]]:
        """
        Fetches every deal item from the Deals Board.
        Returns a list of clean, flat dictionaries ready for Pandas.
        """
        if not MONDAY_BOARD_ID_DEALS:
            logger.warning("MONDAY_BOARD_ID_DEALS is not set. Cannot fetch from Monday API.")
            return []
        return self._fetch_all_items(MONDAY_BOARD_ID_DEALS)

    def get_work_orders(self) -> List[Dict[str, Any]]:
        """
        Fetches every work order item from the Work Orders Board.
        Returns a list of clean, flat dictionaries ready for Pandas.
        """
        if not MONDAY_BOARD_ID_WORK_ORDERS:
            logger.warning("MONDAY_BOARD_ID_WORK_ORDERS is not set. Cannot fetch from Monday API.")
            return []
        return self._fetch_all_items(MONDAY_BOARD_ID_WORK_ORDERS)


if __name__ == "__main__":
    try:
        if not MONDAY_API_KEY:
            raise ValueError("MONDAY_API_KEY is missing in your environment configuration.")
            
        client = MondayClient()
        deals = client.get_deals()
        work_orders = client.get_work_orders()
        
        print("----------------------------------------")
        print("Monday API Connection Test")
        print("----------------------------------------")
        print(f"Deals Loaded: {len(deals)}")
        print(f"Work Orders Loaded: {len(work_orders)}")
        
    except Exception as e:
        print("----------------------------------------")
        print("Monday API Connection Test")
        print("----------------------------------------")
        print(f"Python Error: {str(e)}")