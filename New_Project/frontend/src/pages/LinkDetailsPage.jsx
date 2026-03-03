import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { api } from '../services/api';
import { Copy, ExternalLink, Calendar, Globe, Monitor, Smartphone, Tablet } from 'lucide-react';

export default function LinkDetailsPage({ user }) {
  const { linkId } = useParams();
  const [link, setLink] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchLinkDetails = async () => {
      try {
        const response = await api.get(`/links/${linkId}`);
        setLink(response.data);
      } catch (error) {
        console.error('Error fetching link details:', error);
        toast.error('Gagal memuat detail tautan');
      } finally {
        setLoading(false);
      }
    };
    
    if (linkId) {
      fetchLinkDetails();
    }
  }, [linkId]);
  
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Tautan disalin ke clipboard');
  };
  
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('id-ID', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  const getDeviceIcon = (device) => {
    if (device.toLowerCase().includes('mobile')) return <Smartphone className="w-4 h-4" />;
    if (device.toLowerCase().includes('tablet')) return <Tablet className="w-4 h-4" />;
    return <Monitor className="w-4 h-4" />;
  };
  
  if (loading) {
    return <div className="container mx-auto px-4 py-8">Memuat...</div>;
  }
  
  if (!link) {
    return <div className="container mx-auto px-4 py-8">Tautan tidak ditemukan</div>;
  }
  
  const shortUrl = `${window.location.origin}/api/r/${link.short_code}`;
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <Button onClick={() => window.history.back()} variant="outline">Kembali</Button>
      </div>
      
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Detail Tautan</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">Tautan Pintas</h3>
              <div className="flex items-center space-x-2">
                <a href={shortUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline flex items-center">
                  {shortUrl}
                  <ExternalLink className="ml-1 w-4 h-4" />
                </a>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(shortUrl)}
                >
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            <div>
              <h3 className="font-medium mb-2">URL Tujuan</h3>
              <a href={link.destination_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                {link.destination_url}
              </a>
            </div>
            
            {link.title && (
              <div>
                <h3 className="font-medium mb-2">Judul</h3>
                <p>{link.title}</p>
              </div>
            )}
            
            {link.expiration_date && (
              <div>
                <h3 className="font-medium mb-2 flex items-center">
                  <Calendar className="w-4 h-4 mr-2" />
                  Tanggal Kedaluwarsa
                </h3>
                <p>{formatDate(link.expiration_date)}</p>
                {new Date() > new Date(link.expiration_date) && (
                  <Badge variant="destructive" className="mt-2">Kedaluwarsa</Badge>
                )}
              </div>
            )}
            
            {link.countries && link.countries.length > 0 && (
              <div>
                <h3 className="font-medium mb-2">Negara Target</h3>
                <div className="flex flex-wrap gap-2">
                  {link.countries.map(country => (
                    <Badge key={country} variant="secondary">{country}</Badge>
                  ))}
                </div>
              </div>
            )}
            
            {link.alternative_url && (
              <div>
                <h3 className="font-medium mb-2">URL Alternatif</h3>
                <a href={link.alternative_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  {link.alternative_url}
                </a>
              </div>
            )}
            
            {link.bot_redirect_url && (
              <div>
                <h3 className="font-medium mb-2">URL Pengalihan Bot</h3>
                <a href={link.bot_redirect_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  {link.bot_redirect_url}
                </a>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>Riwayat Klik ({link.clicks?.length || 0})</CardTitle>
        </CardHeader>
        <CardContent>
          {link.clicks && link.clicks.length > 0 ? (
            <div className="space-y-4">
              {link.clicks.map((click) => (
                <div key={click.id} className="border rounded-lg p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-sm">{click.ip_address}</span>
                      {click.country_code && click.country_code !== 'XX' && (
                        <span className="bg-gray-100 px-2 py-1 rounded text-xs">{click.country_code}</span>
                      )}
                    </div>
                    <span className="text-sm text-gray-500">
                      {formatDate(click.timestamp)}
                    </span>
                  </div>
                  
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center space-x-1">
                      {getDeviceIcon(click.device)}
                      <span>{click.device}</span>
                    </div>
                    <div>
                      <span className="font-medium">Browser:</span> {click.browser}
                    </div>
                    <div>
                      <span className="font-medium">OS:</span> {click.os}
                    </div>
                    {click.is_bot && (
                      <Badge variant="destructive">Bot</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">Belum ada klik untuk tautan ini</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}