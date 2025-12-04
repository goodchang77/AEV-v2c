import anthropic
import os

def test_anthropic_api():
    """測試 Anthropic API Key 是否有效"""
    
    # 從環境變數讀取
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ 錯誤: 未設定 ANTHROPIC_API_KEY 環境變數")
        return False
    
    try:
        # 建立客戶端
        client = anthropic.Anthropic(api_key=api_key)
        
        # 發送測試請求
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "請回答: 1+1=?"}
            ]
        )
        
        response = message.content[0].text
        print("✅ API Key 有效!")
        print(f"📝 Claude 回應: {response}")
        return True
        
    except anthropic.AuthenticationError:
        print("❌ 錯誤: API Key 無效")
        return False
    except anthropic.PermissionDeniedError:
        print("❌ 錯誤: API Key 權限不足")
        return False
    except anthropic.RateLimitError:
        print("⚠️ 警告: 超過速率限制，請稍後再試")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        return False

if __name__ == "__main__":
    test_anthropic_api()