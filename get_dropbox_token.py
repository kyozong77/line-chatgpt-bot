import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

APP_KEY = 'a5cyfuzudic0aza'
APP_SECRET = 'znjvd34k44m5z18'

auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)

# 使用授權碼
auth_code = 'MdX_XZHr-kAAAAAAAAABVDW0dv6BZAVVDTd6ajp4mcs'

try:
    # 使用授權碼獲取訪問令牌和刷新令牌
    oauth_result = auth_flow.finish(auth_code)
    print("\n成功！請將以下值添加到環境變量：")
    print(f"\nDROPBOX_REFRESH_TOKEN={oauth_result.refresh_token}")
except Exception as e:
    print('Error: %s' % (e,))
