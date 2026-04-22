import { z } from 'zod';

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es requerido')
    .email('Ingresá un email válido'),
  password: z.string().min(1, 'Ingresá tu contraseña'),
});

export const registerSchema = z.object({
  email: z
    .string()
    .min(1, 'El email es requerido')
    .email('Ingresá un email válido'),
  password: z
    .string()
    .min(1, 'La contraseña es requerida')
    .min(10, 'Mínimo 10 caracteres')
    .max(128, 'Máximo 128 caracteres')
    .regex(/[A-Za-z]/, 'Debe tener al menos una letra')
    .regex(/[0-9]/, 'Debe tener al menos un número'),
  firstName: z.string().max(80).optional(),
  lastName: z.string().max(80).optional(),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;
