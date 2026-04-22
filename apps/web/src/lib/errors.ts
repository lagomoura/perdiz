const ERROR_MESSAGES: Record<string, string> = {
  AUTH_INVALID_CREDENTIALS: 'Email o contraseña incorrectos.',
  AUTH_EMAIL_NOT_VERIFIED: 'Verificá tu email antes de continuar.',
  AUTH_ACCOUNT_LOCKED: 'Demasiados intentos fallidos. Probá en 30 minutos.',
  AUTH_ACCOUNT_SUSPENDED: 'Tu cuenta está suspendida. Contactá a soporte.',
  AUTH_REFRESH_INVALID: 'Tu sesión no es válida. Ingresá de nuevo.',
  AUTH_REFRESH_EXPIRED: 'Tu sesión venció. Ingresá de nuevo.',
  AUTH_REFRESH_REUSED: 'Detectamos actividad sospechosa. Ingresá de nuevo.',
  RESOURCE_CONFLICT: 'Ya existe una cuenta con ese email.',
  VALIDATION_ERROR: 'Los datos enviados no son válidos.',
  RATE_LIMIT_EXCEEDED: 'Demasiadas solicitudes. Esperá unos segundos.',
  BUSINESS_RULE_VIOLATION: 'Tu email ya está verificado.',
};

export function getErrorMessage(code: string, fallback: string): string {
  return ERROR_MESSAGES[code] ?? fallback;
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
