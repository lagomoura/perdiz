import { describe, expect, it } from 'vitest';
import { loginSchema, registerSchema } from '../schemas';

describe('loginSchema', () => {
  it('accepts valid email and non-empty password', () => {
    expect(loginSchema.safeParse({ email: 'a@b.com', password: 'algo' }).success).toBe(true);
  });

  it('rejects invalid email', () => {
    const result = loginSchema.safeParse({ email: 'no-es-email', password: 'algo' });
    expect(result.success).toBe(false);
  });

  it('rejects empty password', () => {
    const result = loginSchema.safeParse({ email: 'a@b.com', password: '' });
    expect(result.success).toBe(false);
  });
});

describe('registerSchema', () => {
  const valid = { email: 'a@b.com', password: 'ValidPass1' };

  it('accepts valid credentials', () => {
    expect(registerSchema.safeParse(valid).success).toBe(true);
  });

  it('accepts optional first/last name', () => {
    expect(
      registerSchema.safeParse({ ...valid, firstName: 'Juan', lastName: 'Pérez' }).success,
    ).toBe(true);
  });

  it('rejects password shorter than 10 chars', () => {
    expect(registerSchema.safeParse({ ...valid, password: 'Short1' }).success).toBe(false);
  });

  it('rejects password without letter', () => {
    expect(registerSchema.safeParse({ ...valid, password: '1234567890' }).success).toBe(false);
  });

  it('rejects password without digit', () => {
    expect(registerSchema.safeParse({ ...valid, password: 'sindigitsss' }).success).toBe(false);
  });

  it('rejects invalid email', () => {
    expect(registerSchema.safeParse({ ...valid, email: 'nodominio' }).success).toBe(false);
  });
});
