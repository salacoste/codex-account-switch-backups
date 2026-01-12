export interface AccountLimits {
    limit_5h?: {
        used: number;
        limit: number;
        reset_in_minutes: number;
    };
    limit_weekly?: {
        used: number;
        limit: number;
        reset_in_days: number;
    };
}

export interface Account {
    name: string;
    email?: string;
    type?: string;
    tags?: string[];
    limits?: AccountLimits;
}

export interface DeviceFlowData {
    device_code: string;
    user_code: string;
    verification_uri: string;
    verification_uri_complete?: string;
    interval: number;
    expires_in: number;
}
