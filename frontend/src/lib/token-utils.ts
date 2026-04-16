/**
 * Token parsing utilities
 * 
 * Token format: "network_id:::TOKEN_SYMBOL###wallet_name"
 * Example: "5010:::TRX###my-wallet"
 */

export interface ParsedToken {
  networkId: string;
  tokenSymbol: string;
  walletName: string;
  raw: string;
}

/**
 * Parse token string into components
 */
export function parseToken(token: string): ParsedToken | null {
  try {
    // Format: "network_id:::TOKEN_SYMBOL###wallet_name"
    const [networkToken, walletName] = token.split('###');
    if (!networkToken) return null;

    const [networkId, tokenSymbol] = networkToken.split(':::');
    
    return {
      networkId: networkId || '',
      tokenSymbol: tokenSymbol || token,
      walletName: walletName || '',
      raw: token,
    };
  } catch (error) {
    console.warn('Failed to parse token:', token, error);
    return null;
  }
}

/**
 * Format token for display (just symbol)
 * Example: "5010:::TRX###my-wallet" -> "TRX"
 */
export function formatTokenSymbol(token: string): string {
  const parsed = parseToken(token);
  return parsed?.tokenSymbol || token;
}

/**
 * Format token with wallet name
 * Example: "5010:::TRX###my-wallet" -> "TRX (my-wallet)"
 */
export function formatTokenWithWallet(token: string): string {
  const parsed = parseToken(token);
  if (!parsed) return token;

  if (parsed.walletName) {
    return `${parsed.tokenSymbol} (${parsed.walletName})`;
  }
  return parsed.tokenSymbol;
}

/**
 * Format full token info
 * Example: "5010:::TRX###my-wallet" -> "TRX • Network 5010 • my-wallet"
 */
export function formatTokenFull(token: string): string {
  const parsed = parseToken(token);
  if (!parsed) return token;

  const parts = [parsed.tokenSymbol];
  if (parsed.networkId) parts.push(`Network ${parsed.networkId}`);
  if (parsed.walletName) parts.push(parsed.walletName);

  return parts.join(' • ');
}

/**
 * Extract just the value from token+value string
 * Example: "500 USDT:::1###wallet" -> "500"
 */
export function extractValue(valueWithToken: string): string {
  const match = valueWithToken.match(/^([\d.,]+)\s/);
  return match ? match[1] : valueWithToken;
}

/**
 * Extract token from value+token string
 * Example: "500 USDT:::1###wallet" -> "USDT:::1###wallet"
 */
export function extractToken(valueWithToken: string): string {
  const match = valueWithToken.match(/^[\d.,]+\s+(.+)/);
  return match ? match[1] : valueWithToken;
}

/**
 * Format value with token symbol
 * Example: "500 USDT:::1###wallet" -> "500 USDT"
 */
export function formatValueWithToken(valueWithToken: string): string {
  const value = extractValue(valueWithToken);
  const token = extractToken(valueWithToken);
  const symbol = formatTokenSymbol(token);
  
  return `${value} ${symbol}`;
}
