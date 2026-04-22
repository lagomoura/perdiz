export interface AuthUser {
  id: string;
  email: string;
  emailVerified: boolean;
  role: 'user' | 'admin';
  firstName: string | null;
  lastName: string | null;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
}
