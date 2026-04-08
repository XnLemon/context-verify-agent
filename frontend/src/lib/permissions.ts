import type { UserMember } from '@/src/types';

export function canUploadOrEditContract(member: UserMember): boolean {
  return member.role === 'employee' && member.member_type !== 'legal';
}

export function canFinalizeContract(member: UserMember): boolean {
  return member.role === 'admin' || member.member_type === 'legal';
}
