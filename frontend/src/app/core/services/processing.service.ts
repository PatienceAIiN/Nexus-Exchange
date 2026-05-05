import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ProcessedFile, ProcessingProgress } from '../models/interfaces';

@Injectable({ providedIn: 'root' })
export class ProcessingService {
  constructor(private http: HttpClient) {}

  uploadFile(file: File): Observable<any> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<any>('/api/processing/upload', form);
  }

  subscribeProgress(taskId: string): EventSource {
    const token = localStorage.getItem('nexus_token');
    return new EventSource(`/api/processing/progress/${taskId}?token=${token}`);
  }

  getHistory(): Observable<ProcessedFile[]> {
    return this.http.get<ProcessedFile[]>('/api/processing/history');
  }

  downloadFile(fileId: number): Observable<Blob> {
    return this.http.get(`/api/processing/download/${fileId}`, { responseType: 'blob' });
  }

  deleteFile(fileId: number): Observable<any> {
    return this.http.delete<any>(`/api/processing/file/${fileId}`);
  }

  deleteFilesBulk(fileIds: number[]): Observable<any> {
    return this.http.post<any>(`/api/processing/files/bulk-delete`, { file_ids: fileIds });
  }
}
